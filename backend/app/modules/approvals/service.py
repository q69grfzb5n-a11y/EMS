from sqlalchemy.orm import Session

from app.modules.approvals.schemas import EmployeeBrief, PendingItemOut
from app.modules.auth.models import User
from app.modules.evaluations import service as evaluations_service
from app.modules.transfers import service as transfers_service


def list_pending_for_actor(db: Session, actor: User) -> list[PendingItemOut]:
    """Unified inbox: merges every evaluation and transfer request the actor's
    role(s) can act on right now (see PLAN §Phase 6 — 'prove the approvals
    engine is generic')."""
    items = [
        PendingItemOut(
            id=e.id,
            entity_type="evaluation",
            kind=e.kind,
            status=e.status,
            employee=EmployeeBrief(
                id=e.employee.id,
                staff_no=e.employee.staff_no,
                full_name_en=e.employee.full_name_en,
                full_name_ar=e.employee.full_name_ar,
            ),
            created_at=e.created_at,
        )
        for e in evaluations_service.list_pending_for_actor(db, actor)
    ]
    items += [
        PendingItemOut(
            id=t.id,
            entity_type="transfer",
            kind="transfer",
            status=t.status,
            employee=EmployeeBrief(
                id=t.employee.id,
                staff_no=t.employee.staff_no,
                full_name_en=t.employee.full_name_en,
                full_name_ar=t.employee.full_name_ar,
            ),
            created_at=t.created_at,
        )
        for t in transfers_service.list_pending_for_actor(db, actor)
    ]
    items.sort(key=lambda i: i.created_at)
    return items
