"""Generic approval state machine: (status, action) -> transition, shared by
every workflow in the system (evaluations now; transfers and incentive runs
reuse the exact same engine + approval_actions table in later phases)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.errors import bad_request, forbidden
from app.common.models import ApprovalAction, Notification
from app.modules.auth.models import User


class WorkflowEntity(Protocol):
    id: int
    status: str


# `Any` rather than WorkflowEntity: each module's guards are written against
# their own concrete entity type (e.g. Evaluation) for real type-checking in
# the guard body; Callable parameters are contravariant, so a guard typed for
# a concrete subtype can't satisfy Callable[[Session, WorkflowEntity, User], bool].
Guard = Callable[[Session, Any, User], bool]


@dataclass(frozen=True)
class TransitionStep:
    to: str
    roles: frozenset[str]
    guard: Guard | None = None


TransitionTable = dict[tuple[str, str], TransitionStep]


def apply_transition(
    db: Session,
    *,
    entity: WorkflowEntity,
    entity_type: str,
    table: TransitionTable,
    action: str,
    actor: User,
    comment: str | None = None,
    notify_user_id: int | None = None,
) -> ApprovalAction:
    """Validates role + guard, mutates entity.status, inserts one approval_actions
    row, optionally notifies one user — one code path for every workflow."""
    step = table.get((entity.status, action))
    if step is None:
        raise bad_request(
            f"Action {action!r} is not valid from status {entity.status!r}",
            code="invalid_transition",
        )

    matching_roles = sorted(step.roles.intersection(actor.role_codes))
    if not matching_roles:
        raise forbidden()

    if step.guard is not None and not step.guard(db, entity, actor):
        raise forbidden()

    from_status = entity.status
    entity.status = step.to

    approval_action = ApprovalAction(
        entity_type=entity_type,
        entity_id=entity.id,
        action=action,
        from_status=from_status,
        to_status=step.to,
        actor_user_id=actor.id,
        actor_role=matching_roles[0],
        comment=comment,
    )
    db.add(approval_action)

    if notify_user_id is not None:
        db.add(
            Notification(
                user_id=notify_user_id,
                entity_type=entity_type,
                entity_id=entity.id,
                message=f"{entity_type} #{entity.id}: {action} ({from_status} -> {step.to})",
            )
        )

    db.flush()
    return approval_action


def transition_history(db: Session, *, entity_type: str, entity_id: int) -> list[ApprovalAction]:
    stmt = (
        select(ApprovalAction)
        .where(ApprovalAction.entity_type == entity_type, ApprovalAction.entity_id == entity_id)
        .order_by(ApprovalAction.created_at)
    )
    return list(db.scalars(stmt))
