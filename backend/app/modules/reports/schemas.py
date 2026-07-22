from decimal import Decimal

from pydantic import BaseModel


class DeptSummaryOut(BaseModel):
    department_id: int
    code: str
    name_en: str
    name_ar: str
    employee_count: int
    total_amount: Decimal


class PeriodSummaryOut(BaseModel):
    period_id: int
    year: int
    month: int
    run_id: int | None
    run_status: str | None
    departments: list[DeptSummaryOut]
    grand_total: Decimal
