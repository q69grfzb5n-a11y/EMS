from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class IncentivePeriodOut(BaseModel):
    id: int
    year: int
    month: int
    target_pool: Decimal | None
    actual_pool: Decimal | None
    status: str


class IncentivePeriodCreateRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class RowIssueOut(BaseModel):
    row_number: int
    staff_no: str | None
    severity: Literal["error", "warning"]
    message: str


class ImportPreviewOut(BaseModel):
    period_id: int
    total_rows: int
    matched_count: int
    unmatched_count: int
    unmatched_staff_nos: list[str]
    issues: list[RowIssueOut]
    has_errors: bool


class AttendanceImportOut(BaseModel):
    id: int
    period_id: int
    original_filename: str
    uploaded_by_user_id: int
    row_count: int
    error_report: list[dict[str, Any]] | None
    status: str
    created_at: datetime


class AttendanceRecordEmployeeBrief(BaseModel):
    id: int
    staff_no: str
    full_name_en: str | None
    full_name_ar: str


class AttendanceRecordOut(BaseModel):
    id: int
    period_id: int
    employee: AttendanceRecordEmployeeBrief
    present: int
    off_days: int
    absent: int
    leave: int
    public_holiday: int
    deduct_min: Decimal
    over_time: Decimal
    approved: int
    pending_approval: int
    submitted: int
    approved_over_time: Decimal


class AttendanceZeroFlagOut(BaseModel):
    id: int
    employee_id: int
    period_from_id: int
    period_to_id: int
    total_leave_absence_days: int
    allowance_days: int
    is_overridden: bool
    override_reason: str | None


class ZeroFlagOverrideRequest(BaseModel):
    reason: str = Field(min_length=1)
