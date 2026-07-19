from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.common.enums import EmploymentStatus


class DepartmentBrief(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: str


class PositionBrief(BaseModel):
    id: int
    code: str
    title_en: str
    title_ar: str


class EmployeeOut(BaseModel):
    id: int
    staff_no: str
    full_name_en: str | None
    full_name_ar: str
    department: DepartmentBrief
    position: PositionBrief
    contract_position_title: str | None
    contract_years: int | None
    contract_start_date: date | None
    employment_status: str
    reviewer_user_id: int | None


class EmployeeCreateRequest(BaseModel):
    staff_no: str
    full_name_ar: str
    full_name_en: str | None = None
    department_id: int
    position_id: int
    contract_position_title: str | None = None
    contract_years: int | None = None
    contract_start_date: date | None = None


class EmployeePatchRequest(BaseModel):
    full_name_ar: str | None = None
    full_name_en: str | None = None
    department_id: int | None = None
    position_id: int | None = None
    contract_position_title: str | None = None
    contract_years: int | None = None
    contract_start_date: date | None = None
    employment_status: EmploymentStatus | None = None


class ReviewerAssignRequest(BaseModel):
    reviewer_user_id: int


class EmployeeSalaryOut(BaseModel):
    id: int
    employee_id: int
    effective_from: date
    effective_to: date | None
    base_salary: Decimal


class EmployeeSalaryCreateRequest(BaseModel):
    effective_from: date
    effective_to: date | None = None
    base_salary: Decimal = Field(ge=0)
