"""Request and response schemas."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Sign-up request."""

    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, description="Plain-text password; hashed before storage.")


class Token(BaseModel):
    """Login token response."""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------


class DepartmentCreate(BaseModel):
    """Create-department request."""

    name: str = Field(min_length=1, max_length=150)


class DepartmentResponse(BaseModel):
    """Department with its employee count."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    employee_count: int = 0


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------


class EmployeeBase(BaseModel):
    """Common employee fields."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    job_title: str = Field(min_length=1, max_length=150)
    salary: Decimal = Field(gt=0)
    hire_date: date
    department_id: int


class EmployeeCreate(EmployeeBase):
    """Create-employee request."""


class EmployeeUpdate(BaseModel):
    """Update-employee request; send only the fields to change."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    salary: Decimal | None = Field(default=None, gt=0)
    hire_date: date | None = None
    department_id: int | None = None


class EmployeeResponse(EmployeeBase):
    """Employee returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class PaginatedEmployees(BaseModel):
    """One page of employees with paging info."""

    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int