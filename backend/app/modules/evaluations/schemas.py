from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class EmployeeBrief(BaseModel):
    id: int
    staff_no: str
    full_name_en: str | None
    full_name_ar: str


class EvaluationScoreOut(BaseModel):
    criterion_id: int
    name_en: str
    name_ar: str
    guidance_en: str | None
    guidance_ar: str | None
    max_marks: int
    input_mode: str
    allow_negative: bool
    raw_input: Decimal | None
    awarded_marks: Decimal | None
    auto_suggested_marks: Decimal | None
    remarks: str | None


class EvaluationOut(BaseModel):
    id: int
    employee: EmployeeBrief
    period_id: int
    kind: str
    status: str
    template_version_id: int
    owner_user_id: int
    activities: list[str] | None
    score_pct: Decimal | None
    grade: str | None
    row_version: int
    scores: list[EvaluationScoreOut]


class EvaluationCreateRequest(BaseModel):
    employee_id: int
    period_id: int
    kind: str = "regular"


class BulkCreateRequest(BaseModel):
    department_id: int
    period_id: int
    kind: str = "regular"


class BulkCreateSkipped(BaseModel):
    employee_id: int
    staff_no: str
    reason: str | None


class BulkCreateResponse(BaseModel):
    created: list[EvaluationOut]
    skipped: list[BulkCreateSkipped]


class ScoreUpdateRequest(BaseModel):
    criterion_id: int
    raw_input: Decimal | None = None
    remarks: str | None = None


class EvaluationUpdateRequest(BaseModel):
    row_version: int
    scores: list[ScoreUpdateRequest]
    activities: list[str] | None = None


class TransitionRequest(BaseModel):
    comment: str | None = None


class ApprovalActionOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    from_status: str
    to_status: str
    actor_user_id: int
    actor_role: str
    comment: str | None
    created_at: datetime
