"""Transition tables for the two evaluation kinds, built on the shared engine
in common/workflow.py. REGULAR: draft -> submitted -> manager_approved, with
a return loop back to `returned` (resubmit re-enters `submitted`). SELF:
draft -> submitted -> pmo_reviewed -> fm_approved, with a return loop from
either review step back to `returned` (resubmit always re-enters PMO review,
never skips straight to FM — keeps the state machine small)."""

from sqlalchemy.orm import Session

from app.common.enums import EvaluationStatus, RoleCode
from app.common.workflow import TransitionStep, TransitionTable
from app.modules.auth.models import User
from app.modules.employees.models import Employee
from app.modules.evaluations.models import Evaluation


def _actor_department_id(db: Session, actor: User) -> int | None:
    if actor.employee_id is None:
        return None
    employee = db.get(Employee, actor.employee_id)
    return employee.department_id if employee is not None else None


def is_owner(_db: Session, evaluation: Evaluation, actor: User) -> bool:
    return evaluation.owner_user_id == actor.id


def is_dept_manager_of_employee(db: Session, evaluation: Evaluation, actor: User) -> bool:
    return _actor_department_id(db, actor) == evaluation.employee.department_id


DRAFT = EvaluationStatus.DRAFT.value
SUBMITTED = EvaluationStatus.SUBMITTED.value
RETURNED = EvaluationStatus.RETURNED.value
MANAGER_APPROVED = EvaluationStatus.MANAGER_APPROVED.value
PMO_REVIEWED = EvaluationStatus.PMO_REVIEWED.value
FM_APPROVED = EvaluationStatus.FM_APPROVED.value

REGULAR_TRANSITIONS: TransitionTable = {
    (DRAFT, "submit"): TransitionStep(
        to=SUBMITTED, roles=frozenset({RoleCode.REVIEWER.value}), guard=is_owner
    ),
    (RETURNED, "submit"): TransitionStep(
        to=SUBMITTED, roles=frozenset({RoleCode.REVIEWER.value}), guard=is_owner
    ),
    (SUBMITTED, "approve"): TransitionStep(
        to=MANAGER_APPROVED,
        roles=frozenset({RoleCode.DEPT_MANAGER.value}),
        guard=is_dept_manager_of_employee,
    ),
    (SUBMITTED, "return"): TransitionStep(
        to=RETURNED,
        roles=frozenset({RoleCode.DEPT_MANAGER.value}),
        guard=is_dept_manager_of_employee,
    ),
}

SELF_APPRAISAL_TRANSITIONS: TransitionTable = {
    (DRAFT, "submit"): TransitionStep(
        to=SUBMITTED, roles=frozenset({RoleCode.KEY_PERSON.value}), guard=is_owner
    ),
    (RETURNED, "submit"): TransitionStep(
        to=SUBMITTED, roles=frozenset({RoleCode.KEY_PERSON.value}), guard=is_owner
    ),
    (SUBMITTED, "review"): TransitionStep(to=PMO_REVIEWED, roles=frozenset({RoleCode.PMO.value})),
    (SUBMITTED, "return"): TransitionStep(to=RETURNED, roles=frozenset({RoleCode.PMO.value})),
    (PMO_REVIEWED, "approve"): TransitionStep(
        to=FM_APPROVED, roles=frozenset({RoleCode.FACTORY_MANAGER.value})
    ),
    (PMO_REVIEWED, "return"): TransitionStep(
        to=RETURNED, roles=frozenset({RoleCode.FACTORY_MANAGER.value})
    ),
}
