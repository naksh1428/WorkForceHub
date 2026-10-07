"""Routes for working with employees.

Results from reading data are saved in Redis so repeat requests are faster.
That saved data is cleared whenever something is added, changed or removed.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.cache import Cache, get_cache
from app.db.database import get_db
from app.models.models import Department, Employee, User
from app.schemas.schemas import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    PaginatedEmployees,
)

router = APIRouter(prefix="/employees", tags=["employees"])

LIST_CACHE_PATTERN = "employees:list:*"
DEPARTMENTS_CACHE_KEY = "departments:all"


def _employee_cache_key(employee_id: int) -> str:
    """Name used to save one employee in the cache."""
    return f"employees:id:{employee_id}"


def _list_cache_key(
    page: int, page_size: int, department_id: int | None, search: str | None
) -> str:
    """Name used to save one page of search results in the cache."""
    return f"employees:list:{page}:{page_size}:{department_id}:{search or ''}"


def _invalidate_employee_caches(cache: Cache, employee_id: int | None = None) -> None:
    """Throw away saved employee and department data so it is not out of date."""
    if employee_id is not None:
        cache.delete_pattern(_employee_cache_key(employee_id))
    cache.delete_pattern(LIST_CACHE_PATTERN)
    cache.delete_pattern(DEPARTMENTS_CACHE_KEY)


@router.get("", response_model=PaginatedEmployees)
def list_employees(
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    page_size: int = Query(10, ge=1, le=100, description="Employees per page (up to 100)"),
    department_id: int | None = Query(None, description="Only this department"),
    search: str | None = Query(
        None, description="Search by first name, last name or email (any case)"
    ),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> PaginatedEmployees:
    """Show employees one page at a time.

    You can also pick a department or search by name or email.
    """
    cache_key = _list_cache_key(page, page_size, department_id, search)
    cached = cache.get(cache_key)
    if cached is not None:
        return PaginatedEmployees(**cached)

    query = db.query(Employee)
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                Employee.email.ilike(pattern),
            )
        )

    total = query.count()
    items = query.order_by(Employee.id).offset((page - 1) * page_size).limit(page_size).all()

    result = PaginatedEmployees(
        items=[EmployeeResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    cache.set(cache_key, result.model_dump())
    return result


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> EmployeeResponse:
    """Add a new employee.

    Fails with 404 if the department does not exist,
    or 409 if another employee already uses this email.
    """
    if db.get(Department, payload.department_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    employee = Employee(**payload.model_dump())
    db.add(employee)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
        ) from exc
    db.refresh(employee)

    _invalidate_employee_caches(cache)
    return EmployeeResponse.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> EmployeeResponse:
    """Show one employee by their id.

    Fails with 404 if the employee does not exist.
    """
    cache_key = _employee_cache_key(employee_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return EmployeeResponse(**cached)

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    result = EmployeeResponse.model_validate(employee)
    cache.set(cache_key, result.model_dump())
    return result


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> EmployeeResponse:
    """Change some details of an employee. Only the fields you send are changed.

    Fails with 404 if the employee or the new department does not exist,
    or 409 if another employee already uses this email.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    updates = payload.model_dump(exclude_unset=True)
    if "department_id" in updates and db.get(Department, updates["department_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    for field, value in updates.items():
        setattr(employee, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
        ) from exc
    db.refresh(employee)

    _invalidate_employee_caches(cache, employee_id)
    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> None:
    """Remove an employee.

    Fails with 404 if the employee does not exist.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    db.delete(employee)
    db.commit()
    _invalidate_employee_caches(cache, employee_id)