from datetime import datetime

from pydantic import BaseModel


class EmployeeBrief(BaseModel):
    id: int
    staff_no: str
    full_name_en: str | None
    full_name_ar: str


class PendingItemOut(BaseModel):
    """One normalized row per entity_type in the unified inbox — evaluations and
    transfer requests are structurally different, so this is deliberately a
    thin projection rather than a union of their full `*Out` schemas."""

    id: int
    entity_type: str
    kind: str
    status: str
    employee: EmployeeBrief
    created_at: datetime


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
