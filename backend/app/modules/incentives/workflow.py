"""Transition table for incentive runs, built on the shared engine in
common/workflow.py — draft -> pmo_audit -> fm_approval -> approved, with a
reject loop from either review step straight back to draft (no separate
"returned" status needed: a rejected run just needs more editing in draft,
same simplification transfers made). Unlike evaluations/transfers there is no
per-actor ownership guard: an incentive run is an org-wide administrative
artifact, not a personal request, so any role-holder may act on any run."""

from app.common.enums import IncentiveRunStatus, RoleCode
from app.common.workflow import TransitionStep, TransitionTable

DRAFT = IncentiveRunStatus.DRAFT.value
PMO_AUDIT = IncentiveRunStatus.PMO_AUDIT.value
FM_APPROVAL = IncentiveRunStatus.FM_APPROVAL.value
APPROVED = IncentiveRunStatus.APPROVED.value

RUN_CREATOR_ROLES = frozenset(
    {RoleCode.HR.value, RoleCode.PMO.value, RoleCode.ADMIN.value}
)

RUN_TRANSITIONS: TransitionTable = {
    (DRAFT, "submit_audit"): TransitionStep(to=PMO_AUDIT, roles=RUN_CREATOR_ROLES),
    (PMO_AUDIT, "complete_audit"): TransitionStep(
        to=FM_APPROVAL, roles=frozenset({RoleCode.PMO.value})
    ),
    (PMO_AUDIT, "reject"): TransitionStep(to=DRAFT, roles=frozenset({RoleCode.PMO.value})),
    (FM_APPROVAL, "approve"): TransitionStep(
        to=APPROVED, roles=frozenset({RoleCode.FACTORY_MANAGER.value})
    ),
    (FM_APPROVAL, "reject"): TransitionStep(
        to=DRAFT, roles=frozenset({RoleCode.FACTORY_MANAGER.value})
    ),
}
