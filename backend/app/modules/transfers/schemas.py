from datetime import date

from pydantic import BaseModel


class EmployeeBrief(BaseModel):
    id: int
    staff_no: str
    full_name_en: str | None
    full_name_ar: str


class DepartmentBrief(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: str


class TransferRequestOut(BaseModel):
    id: int
    employee: EmployeeBrief
    from_department: DepartmentBrief
    to_department: DepartmentBrief
    effective_date: date
    reason: str | None
    status: str
    requested_by_user_id: int


class TransferCreateRequest(BaseModel):
    employee_id: int
    to_department_id: int
    effective_date: date
    reason: str | None = None


class TransitionRequest(BaseModel):
    comment: str | None = None
