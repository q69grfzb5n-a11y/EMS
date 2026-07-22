from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.models import AuditLog


@dataclass
class AuditLogPage:
    items: list[AuditLog]
    total: int


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    actor_user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> AuditLogPage:
    conditions = []
    if entity_type is not None:
        conditions.append(AuditLog.entity_type == entity_type)
    if actor_user_id is not None:
        conditions.append(AuditLog.actor_user_id == actor_user_id)
    if date_from is not None:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to is not None:
        conditions.append(AuditLog.created_at <= date_to)

    count_stmt = select(func.count()).select_from(AuditLog)
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        stmt = stmt.where(*conditions)

    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.limit(limit).offset(offset)))
    return AuditLogPage(items=items, total=total)
