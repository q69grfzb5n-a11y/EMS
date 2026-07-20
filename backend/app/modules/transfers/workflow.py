"""Transition table for transfer requests, built on the shared engine in
common/workflow.py — same shape as SELF_APPRAISAL_TRANSITIONS in
evaluations/workflow.py: draft -> submitted -> pmo_reviewed -> fm_approved,
with a return loop from either review step back to `returned`. `applied` is
reached outside this table entirely (see transfers/service.py)."""

from sqlalchemy.orm import Session

from app.common.enums import RoleCode, TransferStatus
from app.common.workflow import TransitionStep, TransitionTable
from app.modules.auth.models import User
from app.modules.transfers.models import TransferRequest

# Roles allowed to request a transfer: HR/ADMIN org-wide, dept managers for
# their own team (scoped further in service.py's create_transfer).
REQUESTER_ROLES = frozenset(
    {RoleCode.HR.value, RoleCode.DEPT_MANAGER.value, RoleCode.ADMIN.value}
)


def is_requester(_db: Session, transfer: TransferRequest, actor: User) -> bool:
    return transfer.requested_by_user_id == actor.id


DRAFT = TransferStatus.DRAFT.value
SUBMITTED = TransferStatus.SUBMITTED.value
RETURNED = TransferStatus.RETURNED.value
PMO_REVIEWED = TransferStatus.PMO_REVIEWED.value
FM_APPROVED = TransferStatus.FM_APPROVED.value

TRANSFER_TRANSITIONS: TransitionTable = {
    (DRAFT, "submit"): TransitionStep(to=SUBMITTED, roles=REQUESTER_ROLES, guard=is_requester),
    (RETURNED, "submit"): TransitionStep(to=SUBMITTED, roles=REQUESTER_ROLES, guard=is_requester),
    (SUBMITTED, "review"): TransitionStep(to=PMO_REVIEWED, roles=frozenset({RoleCode.PMO.value})),
    (SUBMITTED, "return"): TransitionStep(to=RETURNED, roles=frozenset({RoleCode.PMO.value})),
    (PMO_REVIEWED, "approve"): TransitionStep(
        to=FM_APPROVED, roles=frozenset({RoleCode.FACTORY_MANAGER.value})
    ),
    (PMO_REVIEWED, "return"): TransitionStep(
        to=RETURNED, roles=frozenset({RoleCode.FACTORY_MANAGER.value})
    ),
}
