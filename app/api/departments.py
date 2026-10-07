"""Routes for working with departments."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.cache import Cache, get_cache
from app.db.database import get_db
from app.models.models import Department, Employee, User
from app.schemas.schemas import DepartmentCreate, DepartmentResponse

router = APIRouter(prefix="/departments", tags=["departments"])

CACHE_KEY_ALL = "departments:all"
EMPLOYEES_CACHE_PATTERN = "employees:*"


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> list[DepartmentResponse]:
    """Show every department and how many employees are in each one."""
    cached = cache.get(CACHE_KEY_ALL)
    if cached is not None:
        return [DepartmentResponse(**item) for item in cached]

    rows = (
        db.query(Department, func.count(Employee.id))
        .outerjoin(Employee, Employee.department_id == Department.id)
        .group_by(Department.id)
        .order_by(Department.id)
        .all()
    )
    result = [
        DepartmentResponse(id=dept.id, name=dept.name, employee_count=count)
        for dept, count in rows
    ]
    cache.set(CACHE_KEY_ALL, [r.model_dump() for r in result])
    return result


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> DepartmentResponse:
    """Add a new department.

    Fails with 409 if a department with this name already exists.
    """
    department = Department(name=payload.name)
    db.add(department)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Department already exists"
        ) from exc
    db.refresh(department)

    cache.delete_pattern(CACHE_KEY_ALL)
    return DepartmentResponse(id=department.id, name=department.name, employee_count=0)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(get_current_user),
) -> None:
    """Remove a department. All employees in it are removed too.

    Fails with 404 if the department does not exist.
    """
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    db.delete(department)
    db.commit()

    cache.delete_pattern(CACHE_KEY_ALL)
    cache.delete_pattern(EMPLOYEES_CACHE_PATTERN)