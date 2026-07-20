from datetime import date

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.common.audit import write_audit
from app.common.enums import RoleCode, TransferStatus
from app.common.errors import bad_request, conflict, forbidden, not_found
from app.common.models import ApprovalAction
from app.common.workflow import apply_transition, transition_history
from app.modules.auth.models import User
from app.modules.employees.models import Employee
from app.modules.employees.service import get_employee
from app.modules.org.service import get_department
from app.modules.transfers.models import TransferRequest
from app.modules.transfers.workflow import (
    PMO_REVIEWED,
    REQUESTER_ROLES,
    SUBMITTED,
    TRANSFER_TRANSITIONS,
)

# Roles with unrestricted visibility across every transfer request, mirrors
# evaluations.service.FULL_ACCESS_ROLES.
FULL_ACCESS_ROLES = {
    RoleCode.HR.value,
    RoleCode.ADMIN.value,
    RoleCode.PMO.value,
    RoleCode.FACTORY_MANAGER.value,
}
# Roles allowed to request for any employee, not just their own department.
ORG_WIDE_REQUESTER_ROLES = {RoleCode.HR.value, RoleCode.ADMIN.value}


def _actor_department_id(db: Session, actor: User) -> int | None:
    if actor.employee_id is None:
        return None
    employee = db.get(Employee, actor.employee_id)
    return employee.department_id if employee is not None else None


def _transfer_query() -> Select[tuple[TransferRequest]]:
    return select(TransferRequest).options(
        selectinload(TransferRequest.employee),
        selectinload(TransferRequest.from_department),
        selectinload(TransferRequest.to_department),
    )


def get_transfer(db: Session, transfer_id: int) -> TransferRequest:
    transfer = db.scalars(_transfer_query().where(TransferRequest.id == transfer_id)).first()
    if transfer is None:
        raise not_found("Transfer request not found")
    return transfer


def _apply_due_transfers(db: Session) -> None:
    """Effective-dated apply, run lazily on every transfer read/write: this
    project has no background scheduler, so `fm_approved` requests whose
    `effective_date` has arrived are applied (department_id updated, status
    -> applied) the next time anyone touches the transfers module, rather than
    at the exact moment the date rolls over."""
    today = date.today()
    due = list(
        db.scalars(
            select(TransferRequest).where(
                TransferRequest.status == TransferStatus.FM_APPROVED.value,
                TransferRequest.effective_date <= today,
            )
        )
    )
    if not due:
        return
    for transfer in due:
        employee = db.get(Employee, transfer.employee_id)
        assert employee is not None
        before_department_id = employee.department_id
        employee.department_id = transfer.to_department_id
        transfer.status = TransferStatus.APPLIED.value
        write_audit(
            db,
            actor_user_id=transfer.requested_by_user_id,
            action="apply_transfer",
            entity_type="transfer",
            entity_id=transfer.id,
            before={"department_id": before_department_id},
            after={"department_id": transfer.to_department_id},
        )
    db.commit()


def can_view_transfer(db: Session, actor: User, transfer: TransferRequest) -> bool:
    role_codes = set(actor.role_codes)
    if FULL_ACCESS_ROLES.intersection(role_codes):
        return True
    if transfer.requested_by_user_id == actor.id:
        return True
    if RoleCode.DEPT_MANAGER.value in role_codes:
        dept_id = _actor_department_id(db, actor)
        return dept_id is not None and dept_id in (
            transfer.from_department_id,
            transfer.to_department_id,
        )
    return False


def list_transfers_scoped(db: Session, actor: User) -> list[TransferRequest]:
    _apply_due_transfers(db)
    role_codes = set(actor.role_codes)
    stmt = _transfer_query()

    if FULL_ACCESS_ROLES.intersection(role_codes):
        return list(db.scalars(stmt))

    if RoleCode.DEPT_MANAGER.value in role_codes:
        dept_id = _actor_department_id(db, actor)
        if dept_id is None:
            return []
        stmt = stmt.where(
            or_(
                TransferRequest.from_department_id == dept_id,
                TransferRequest.to_department_id == dept_id,
            )
        )
        return list(db.scalars(stmt))

    return list(db.scalars(stmt.where(TransferRequest.requested_by_user_id == actor.id)))


def get_transfer_scoped(db: Session, actor: User, transfer_id: int) -> TransferRequest:
    _apply_due_transfers(db)
    transfer = get_transfer(db, transfer_id)
    if not can_view_transfer(db, actor, transfer):
        raise forbidden()
    return transfer


def list_pending_for_actor(db: Session, actor: User) -> list[TransferRequest]:
    """Feeds the unified approvals inbox (see app/modules/approvals)."""
    _apply_due_transfers(db)
    role_codes = set(actor.role_codes)
    clauses = []

    if REQUESTER_ROLES.intersection(role_codes):
        clauses.append(
            and_(
                TransferRequest.requested_by_user_id == actor.id,
                TransferRequest.status.in_(
                    [TransferStatus.DRAFT.value, TransferStatus.RETURNED.value]
                ),
            )
        )
    if RoleCode.PMO.value in role_codes:
        clauses.append(TransferRequest.status == SUBMITTED)
    if RoleCode.FACTORY_MANAGER.value in role_codes:
        clauses.append(TransferRequest.status == PMO_REVIEWED)

    if not clauses:
        return []
    return list(db.scalars(_transfer_query().where(or_(*clauses))))


def get_history(db: Session, transfer_id: int) -> list[ApprovalAction]:
    get_transfer(db, transfer_id)  # 404 if missing
    return transition_history(db, entity_type="transfer", entity_id=transfer_id)


def create_transfer(
    db: Session,
    actor: User,
    *,
    employee_id: int,
    to_department_id: int,
    effective_date: date,
    reason: str | None,
) -> TransferRequest:
    employee = get_employee(db, employee_id)
    role_codes = set(actor.role_codes)

    if (
        not ORG_WIDE_REQUESTER_ROLES.intersection(role_codes)
        and _actor_department_id(db, actor) != employee.department_id
    ):
        raise forbidden()

    get_department(db, to_department_id)  # 404 if missing
    if to_department_id == employee.department_id:
        raise bad_request(
            "Employee is already in the target department", code="same_department"
        )

    existing_pending = db.scalars(
        select(TransferRequest).where(
            TransferRequest.employee_id == employee_id,
            TransferRequest.status.in_(
                [
                    TransferStatus.DRAFT.value,
                    TransferStatus.SUBMITTED.value,
                    TransferStatus.PMO_REVIEWED.value,
                    TransferStatus.FM_APPROVED.value,
                ]
            ),
        )
    ).first()
    if existing_pending is not None:
        raise conflict(
            "This employee already has a transfer request in progress",
            code="employee_has_pending_transfer",
        )

    transfer = TransferRequest(
        employee_id=employee_id,
        from_department_id=employee.department_id,
        to_department_id=to_department_id,
        effective_date=effective_date,
        reason=reason,
        requested_by_user_id=actor.id,
    )
    db.add(transfer)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_transfer",
        entity_type="transfer",
        entity_id=transfer.id,
        after={
            "employee_id": employee_id,
            "from_department_id": employee.department_id,
            "to_department_id": to_department_id,
            "effective_date": str(effective_date),
        },
    )
    db.commit()
    return get_transfer(db, transfer.id)


def perform_transition(
    db: Session, actor: User, transfer_id: int, *, action: str, comment: str | None = None
) -> TransferRequest:
    transfer = get_transfer(db, transfer_id)
    notify_user_id = None if action == "submit" else transfer.requested_by_user_id
    apply_transition(
        db,
        entity=transfer,
        entity_type="transfer",
        table=TRANSFER_TRANSITIONS,
        action=action,
        actor=actor,
        comment=comment,
        notify_user_id=notify_user_id,
    )
    db.commit()
    _apply_due_transfers(db)
    return get_transfer(db, transfer.id)
