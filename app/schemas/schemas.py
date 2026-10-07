"""Shapes of the data the API takes in and sends back."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """What you send to create an account."""

    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, description="Your password. It is scrambled before saving.")


class Token(BaseModel):
    """The login token you get back after signing up or logging in."""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------


class DepartmentCreate(BaseModel):
    """What you send to add a department."""

    name: str = Field(min_length=1, max_length=150)


class DepartmentResponse(BaseModel):
    """A department and how many employees it has."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    employee_count: int = 0


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------


class EmployeeBase(BaseModel):
    """Details every employee has."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    job_title: str = Field(min_length=1, max_length=150)
    salary: Decimal = Field(gt=0)
    hire_date: date
    department_id: int


class EmployeeCreate(EmployeeBase):
    """What you send to add an employee."""


class EmployeeUpdate(BaseModel):
    """What you send to change an employee. Only send the fields you want to change."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    job_title: str | None = Field(default=None, min_length=1, max_length=150)
    salary: Decimal | None = Field(default=None, gt=0)
    hire_date: date | None = None
    department_id: int | None = None


class EmployeeResponse(EmployeeBase):
    """An employee as the API sends it back."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class PaginatedEmployees(BaseModel):
    """One page of employees, plus the total count and page details."""

    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int