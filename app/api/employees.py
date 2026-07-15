"""Employee endpoints: paginated list, create, get, update, delete.

Caching strategy: `GET` responses are cached in Redis (`employees:id:{id}`,
`employees:list:{page}:{page_size}:{department_id}:{search}`). Any write
(POST/PATCH/DELETE) invalidates the affected key patterns so subsequent
reads never observe stale data.
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
    """Build the cache key for a single employee lookup."""
    return f"employees:id:{employee_id}"


def _list_cache_key(
    page: int, page_size: int, department_id: int | None, search: str | None
) -> str:
    """Build a cache key that uniquely identifies one list query's parameters."""
    return f"employees:list:{page}:{page_size}:{department_id}:{search or ''}"


def _invalidate_employee_caches(cache: Cache, employee_id: int | None = None) -> None:
    """Invalidate list caches (and optionally a single-employee cache).

    Called after any write so reads are always consistent. Also invalidates
    the departments cache, since department employee counts change too.
    """
    if employee_id is not None:
        cache.delete_pattern(_employee_cache_key(employee_id))
    cache.delete_pattern(LIST_CACHE_PATTERN)
    cache.delete_pattern(DEPARTMENTS_CACHE_KEY)


@router.get("", response_model=PaginatedEmployees)
def list_employees(
    page: int = Query(1, ge=1, description="1-indexed page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    department_id: int | None = Query(None, description="Filter by department id"),
    search: str | None = Query(
        None, description="Case-insensitive match on first name, last name or email"
    ),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> PaginatedEmployees:
    """List employees with pagination, optional department filter and search.

    Args:
        page: 1-indexed page number.
        page_size: Number of employees per page (1-100).
        department_id: If given, only employees in this department are returned.
        search: If given, filters on first name, last name or email (ILIKE).
        db: Database session, injected.
        cache: Redis cache wrapper, injected.

    Returns:
        A page of employees plus pagination metadata (`total`, `page`, `page_size`).
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
    """Create a new employee.

    Args:
        payload: New employee's details, including its department id.
        db: Database session, injected.
        cache: Redis cache wrapper, injected.

    Returns:
        The created employee.

    Raises:
        HTTPException: 404 Not Found if the given department doesn't exist.
        HTTPException: 409 Conflict if the email is already in use.
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
    """Fetch a single employee by id, served from cache when available.

    Args:
        employee_id: Primary key of the employee to fetch.
        db: Database session, injected.
        cache: Redis cache wrapper, injected.

    Returns:
        The matching employee.

    Raises:
        HTTPException: 404 Not Found if no employee with that id exists.
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
    """Partially update an employee; only fields present in the payload change.

    Args:
        employee_id: Primary key of the employee to update.
        payload: Subset of employee fields to overwrite. Fields omitted from
            the request body are left untouched (standard PATCH semantics).
        db: Database session, injected.
        cache: Redis cache wrapper, injected.

    Returns:
        The updated employee.

    Raises:
        HTTPException: 404 Not Found if the employee, or (when being
            changed) the new department, doesn't exist.
        HTTPException: 409 Conflict if the new email is already in use.
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
    """Delete an employee.

    Args:
        employee_id: Primary key of the employee to remove.
        db: Database session, injected.
        cache: Redis cache wrapper, injected.

    Raises:
        HTTPException: 404 Not Found if no employee with that id exists.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    db.delete(employee)
    db.commit()
    _invalidate_employee_caches(cache, employee_id)