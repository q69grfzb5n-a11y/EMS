from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class DepartmentBrief(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: str


class EmployeeBrief(BaseModel):
    id: int
    staff_no: str
    full_name_en: str | None
    full_name_ar: str
    department: DepartmentBrief


class ExceptionOut(BaseModel):
    employee_id: int
    staff_no: str
    reason: str | None


class IncentiveLineItemOut(BaseModel):
    id: int
    employee: EmployeeBrief
    evaluation_id: int | None
    evaluation_pct: Decimal
    formula_mode: str
    flat_ref_amount: Decimal | None
    base_salary: Decimal | None
    position_incentive_pct: Decimal | None
    attendance_factor: Decimal
    target_ratio: Decimal
    computed_amount: Decimal
    override_amount: Decimal | None
    override_reason: str | None
    final_amount: Decimal
    is_excluded: bool
    exclude_reason: str | None
    row_version: int


class IncentiveRunOut(BaseModel):
    id: int
    period_id: int
    run_no: int
    status: str
    params: dict[str, Any]
    exceptions: list[ExceptionOut]
    created_by_user_id: int
    total_final_amount: Decimal
    lines: list[IncentiveLineItemOut]


class RunCreateRequest(BaseModel):
    period_id: int
    formula_mode: str = "legacy_flat"
    rounding_step: Decimal = Decimal(10)
    rounding_mode: str = "CEILING"


class LineUpdateRequest(BaseModel):
    row_version: int
    attendance_factor: Decimal | None = None
    override_amount: Decimal | None = None
    override_reason: str | None = None
    clear_override: bool = False
    is_excluded: bool | None = None
    exclude_reason: str | None = None


class TransitionRequest(BaseModel):
    comment: str | None = None
