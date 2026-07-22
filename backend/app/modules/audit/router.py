from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.common.enums import RoleCode
from app.common.models import AuditLog
from app.core.deps import DbSession, require_roles
from app.modules.audit import service
from app.modules.audit.schemas import AuditLogListOut, AuditLogOut
from app.modules.auth.models import User

AuditReaders = Annotated[User, Depends(require_roles(RoleCode.HR, RoleCode.ADMIN))]

router = APIRouter(prefix="/audit-log", tags=["audit"])


def _to_out(log: AuditLog, staff_no_by_user_id: dict[int, str]) -> AuditLogOut:
    return AuditLogOut(
        id=log.id,
        actor_user_id=log.actor_user_id,
        actor_staff_no=staff_no_by_user_id.get(log.actor_user_id) if log.actor_user_id else None,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        before=log.before,
        after=log.after,
        created_at=log.created_at,
    )


@router.get("", response_model=AuditLogListOut)
def list_audit_log_endpoint(
    _actor: AuditReaders,
    db: DbSession,
    entity_type: str | None = None,
    actor_user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogListOut:
    page = service.list_audit_logs(
        db,
        entity_type=entity_type,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    user_ids = {log.actor_user_id for log in page.items if log.actor_user_id is not None}
    staff_no_by_user_id: dict[int, str] = {}
    if user_ids:
        staff_no_by_user_id = {
            u.id: u.staff_no for u in db.scalars(select(User).where(User.id.in_(user_ids)))
        }
    return AuditLogListOut(
        items=[_to_out(log, staff_no_by_user_id) for log in page.items], total=page.total
    )
