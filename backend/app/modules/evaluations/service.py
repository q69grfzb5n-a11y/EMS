from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.common.audit import write_audit
from app.common.enums import (
    EmploymentStatus,
    EvaluationKind,
    EvaluationStatus,
    PeriodStatus,
    RoleCode,
)
from app.common.errors import AppError, bad_request, conflict, forbidden, not_found
from app.common.models import ApprovalAction
from app.common.workflow import TransitionTable, apply_transition, transition_history
from app.modules.attendance.models import AttendanceRecord, AttendanceZeroFlag, IncentivePeriod
from app.modules.attendance.service import get_period
from app.modules.auth.models import User
from app.modules.employees.models import Employee
from app.modules.employees.service import get_employee, get_reviewer_assignment
from app.modules.evaluations.models import Evaluation, EvaluationScore
from app.modules.evaluations.scoring import awarded_marks_for_input, summarize_scores
from app.modules.evaluations.suggestions import suggest_marks
from app.modules.evaluations.workflow import REGULAR_TRANSITIONS, SELF_APPRAISAL_TRANSITIONS
from app.modules.kpi_templates.models import KpiTemplateVersion
from app.modules.kpi_templates.service import get_active_version, resolve_template_for_position

# Roles with unrestricted visibility across every evaluation. Deliberately
# narrower than employees.service.FULL_ACCESS_ROLES: FINANCE has no business
# reason to see performance-evaluation content, unlike the employee roster or
# incentive payouts it's otherwise trusted with.
FULL_ACCESS_ROLES = {
    RoleCode.HR.value,
    RoleCode.ADMIN.value,
    RoleCode.PMO.value,
    RoleCode.FACTORY_MANAGER.value,
}


def _actor_department_id(db: Session, actor: User) -> int | None:
    if actor.employee_id is None:
        return None
    employee = db.get(Employee, actor.employee_id)
    return employee.department_id if employee is not None else None


def _ensure_period_open(period: IncentivePeriod) -> None:
    """A period locked by an approved incentive run (Phase 7) can no longer
    have its evaluations created, scored, or transitioned — the run's line
    items already snapshotted whatever was approved at lock time."""
    if period.status == PeriodStatus.LOCKED.value:
        raise conflict(
            "This period is locked; evaluations can no longer be changed", code="period_locked"
        )


def _evaluation_query() -> Select[tuple[Evaluation]]:
    return select(Evaluation).options(
        selectinload(Evaluation.employee),
        selectinload(Evaluation.template_version).selectinload(KpiTemplateVersion.criteria),
        selectinload(Evaluation.scores),
    )


def get_evaluation(db: Session, evaluation_id: int) -> Evaluation:
    evaluation = db.scalars(_evaluation_query().where(Evaluation.id == evaluation_id)).first()
    if evaluation is None:
        raise not_found("Evaluation not found")
    return evaluation


def can_view_evaluation(db: Session, actor: User, evaluation: Evaluation) -> bool:
    role_codes = set(actor.role_codes)
    if FULL_ACCESS_ROLES.intersection(role_codes):
        return True
    if evaluation.owner_user_id == actor.id:
        return True
    if actor.employee_id is not None and actor.employee_id == evaluation.employee_id:
        return True
    if RoleCode.DEPT_MANAGER.value in role_codes:
        return _actor_department_id(db, actor) == evaluation.employee.department_id
    return False


def get_evaluation_scoped(db: Session, actor: User, evaluation_id: int) -> Evaluation:
    evaluation = get_evaluation(db, evaluation_id)
    if not can_view_evaluation(db, actor, evaluation):
        raise forbidden()
    return evaluation


def list_evaluations_scoped(
    db: Session, actor: User, *, period_id: int | None = None
) -> list[Evaluation]:
    role_codes = set(actor.role_codes)
    stmt = _evaluation_query()
    if period_id is not None:
        stmt = stmt.where(Evaluation.period_id == period_id)

    if FULL_ACCESS_ROLES.intersection(role_codes):
        return list(db.scalars(stmt))

    if RoleCode.DEPT_MANAGER.value in role_codes:
        dept_id = _actor_department_id(db, actor)
        if dept_id is None:
            return []
        stmt = stmt.where(
            Evaluation.employee_id.in_(select(Employee.id).where(Employee.department_id == dept_id))
        )
        return list(db.scalars(stmt))

    conditions = [Evaluation.owner_user_id == actor.id]
    if actor.employee_id is not None:
        conditions.append(Evaluation.employee_id == actor.employee_id)
    stmt = stmt.where(or_(*conditions))
    return list(db.scalars(stmt))


def list_pending_for_actor(db: Session, actor: User) -> list[Evaluation]:
    """Unified inbox: every evaluation the actor's role(s) can act on right now."""
    role_codes = set(actor.role_codes)
    clauses = []

    if RoleCode.REVIEWER.value in role_codes or RoleCode.KEY_PERSON.value in role_codes:
        clauses.append(
            and_(
                Evaluation.owner_user_id == actor.id,
                Evaluation.status.in_(
                    [EvaluationStatus.DRAFT.value, EvaluationStatus.RETURNED.value]
                ),
            )
        )
    if RoleCode.DEPT_MANAGER.value in role_codes:
        dept_id = _actor_department_id(db, actor)
        if dept_id is not None:
            clauses.append(
                and_(
                    Evaluation.status == EvaluationStatus.SUBMITTED.value,
                    Evaluation.kind == EvaluationKind.REGULAR.value,
                    Evaluation.employee_id.in_(
                        select(Employee.id).where(Employee.department_id == dept_id)
                    ),
                )
            )
    if RoleCode.PMO.value in role_codes:
        clauses.append(
            and_(
                Evaluation.status == EvaluationStatus.SUBMITTED.value,
                Evaluation.kind == EvaluationKind.SELF_APPRAISAL.value,
            )
        )
    if RoleCode.FACTORY_MANAGER.value in role_codes:
        clauses.append(Evaluation.status == EvaluationStatus.PMO_REVIEWED.value)

    if not clauses:
        return []
    return list(db.scalars(_evaluation_query().where(or_(*clauses))))


def get_history(db: Session, evaluation_id: int) -> list[ApprovalAction]:
    get_evaluation(db, evaluation_id)  # 404 if missing
    return transition_history(db, entity_type="evaluation", entity_id=evaluation_id)


def _resolve_owner_user_id(db: Session, employee: Employee, kind: str) -> int | None:
    if kind == EvaluationKind.SELF_APPRAISAL.value:
        user = db.scalars(select(User).where(User.employee_id == employee.id)).first()
        return user.id if user is not None else None
    assignment = get_reviewer_assignment(db, employee.id)
    return assignment.reviewer_user_id if assignment is not None else None


def _period_covers(
    period_from: IncentivePeriod, period_to: IncentivePeriod, target: IncentivePeriod
) -> bool:
    return (
        (period_from.year, period_from.month)
        <= (target.year, target.month)
        <= (
            period_to.year,
            period_to.month,
        )
    )


def _has_active_zero_flag(db: Session, employee_id: int, period: IncentivePeriod) -> bool:
    flags = list(
        db.scalars(
            select(AttendanceZeroFlag).where(
                AttendanceZeroFlag.employee_id == employee_id,
                AttendanceZeroFlag.is_overridden.is_(False),
            )
        )
    )
    if not flags:
        return False
    period_ids = {f.period_from_id for f in flags} | {f.period_to_id for f in flags}
    periods_by_id = {
        p.id: p
        for p in db.scalars(select(IncentivePeriod).where(IncentivePeriod.id.in_(period_ids)))
    }
    for flag in flags:
        period_from = periods_by_id.get(flag.period_from_id)
        period_to = periods_by_id.get(flag.period_to_id)
        if (
            period_from is not None
            and period_to is not None
            and _period_covers(period_from, period_to, period)
        ):
            return True
    return False


def _get_attendance_record(
    db: Session, employee_id: int, period_id: int
) -> AttendanceRecord | None:
    return db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id, AttendanceRecord.period_id == period_id
        )
    ).first()


def _recompute_score(db: Session, evaluation: Evaluation) -> None:
    version = db.get(KpiTemplateVersion, evaluation.template_version_id)
    assert version is not None
    max_marks_by_criterion = {c.id: c.max_marks for c in version.criteria}
    pairs = [
        (score.awarded_marks, max_marks_by_criterion[score.criterion_id])
        for score in evaluation.scores
    ]
    summary = summarize_scores(pairs)
    evaluation.score_pct = summary.score_pct
    evaluation.grade = summary.grade


@dataclass
class CreateEvaluationOutcome:
    evaluation: Evaluation | None
    error_code: str | None


_ERROR_MESSAGES: dict[str, str] = {
    "already_exists": "An evaluation already exists for this employee/period/kind",
    "no_template_assigned": "No KPI template is assigned to this employee's position",
    "no_active_template_version": "The assigned KPI template has no active version",
    "no_owner_resolved": "No reviewer could be resolved for this employee — assign one first",
}


def _raise_for_error_code(error_code: str) -> AppError:
    message = _ERROR_MESSAGES.get(error_code, "Could not create evaluation")
    if error_code == "already_exists":
        return conflict(message, code=error_code)
    return bad_request(message, code=error_code)


def _create_evaluation_internal(
    db: Session, actor: User, *, employee: Employee, period: IncentivePeriod, kind: str
) -> CreateEvaluationOutcome:
    existing = db.scalars(
        select(Evaluation).where(
            Evaluation.employee_id == employee.id,
            Evaluation.period_id == period.id,
            Evaluation.kind == kind,
        )
    ).first()
    if existing is not None:
        return CreateEvaluationOutcome(None, "already_exists")

    as_of = date(period.year, period.month, 1)
    template = resolve_template_for_position(db, employee.position_id, as_of)
    if template is None:
        return CreateEvaluationOutcome(None, "no_template_assigned")
    version = get_active_version(db, template.id)
    if version is None:
        return CreateEvaluationOutcome(None, "no_active_template_version")

    owner_user_id = _resolve_owner_user_id(db, employee, kind)
    if owner_user_id is None:
        return CreateEvaluationOutcome(None, "no_owner_resolved")

    evaluation = Evaluation(
        employee_id=employee.id,
        period_id=period.id,
        kind=kind,
        template_version_id=version.id,
        owner_user_id=owner_user_id,
    )
    db.add(evaluation)
    db.flush()

    zero_flag_active = _has_active_zero_flag(db, employee.id, period)
    attendance = _get_attendance_record(db, employee.id, period.id)

    for criterion in version.criteria:
        suggestion = suggest_marks(
            auto_source=criterion.auto_source,
            auto_params=criterion.auto_params,
            max_marks=criterion.max_marks,
            approved_over_time_hours=attendance.approved_over_time if attendance else None,
            absent_days=attendance.absent if attendance else None,
            zero_flag_active=zero_flag_active,
        )
        # Suggestions are only meaningful in "marks" mode — legacy scale_1_5
        # criteria are always manually ranked, never auto-sourced in practice.
        raw_input: Decimal | None = (
            suggestion if (suggestion is not None and criterion.input_mode == "marks") else None
        )
        awarded_marks = (
            awarded_marks_for_input(
                input_mode=criterion.input_mode,
                raw_input=raw_input,
                max_marks=criterion.max_marks,
                allow_negative=criterion.allow_negative,
            )
            if raw_input is not None
            else None
        )
        db.add(
            EvaluationScore(
                evaluation_id=evaluation.id,
                criterion_id=criterion.id,
                raw_input=raw_input,
                awarded_marks=awarded_marks,
                auto_suggested_marks=suggestion,
            )
        )
    db.flush()
    db.refresh(evaluation)
    _recompute_score(db, evaluation)

    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_evaluation",
        entity_type="evaluation",
        entity_id=evaluation.id,
        after={"employee_id": employee.id, "period_id": period.id, "kind": kind},
    )
    return CreateEvaluationOutcome(evaluation, None)


def create_evaluation(
    db: Session, actor: User, *, employee_id: int, period_id: int, kind: str
) -> Evaluation:
    employee = get_employee(db, employee_id)
    period = get_period(db, period_id)
    _ensure_period_open(period)
    outcome = _create_evaluation_internal(db, actor, employee=employee, period=period, kind=kind)
    if outcome.evaluation is None:
        db.rollback()
        assert outcome.error_code is not None
        raise _raise_for_error_code(outcome.error_code)
    db.commit()
    return get_evaluation(db, outcome.evaluation.id)


def create_self_appraisal(db: Session, actor: User, *, period_id: int) -> Evaluation:
    """Self-service counterpart to create_evaluation: a Key Person starts their
    own self-appraisal directly, without going through HR/PMO bulk-create."""
    if RoleCode.KEY_PERSON.value not in actor.role_codes:
        raise forbidden()
    if actor.employee_id is None:
        raise bad_request(
            "Your account is not linked to an employee record", code="no_employee_link"
        )
    employee = get_employee(db, actor.employee_id)
    period = get_period(db, period_id)
    _ensure_period_open(period)
    outcome = _create_evaluation_internal(
        db, actor, employee=employee, period=period, kind=EvaluationKind.SELF_APPRAISAL.value
    )
    if outcome.evaluation is None:
        db.rollback()
        assert outcome.error_code is not None
        raise _raise_for_error_code(outcome.error_code)
    db.commit()
    return get_evaluation(db, outcome.evaluation.id)


@dataclass
class BulkCreateSummary:
    created: list[Evaluation]
    skipped: list[dict[str, object]]


def bulk_create_evaluations(
    db: Session, actor: User, *, department_id: int, period_id: int, kind: str
) -> BulkCreateSummary:
    period = get_period(db, period_id)
    _ensure_period_open(period)
    employees = list(
        db.scalars(
            select(Employee).where(
                Employee.department_id == department_id,
                Employee.employment_status == EmploymentStatus.ACTIVE.value,
            )
        )
    )

    created: list[Evaluation] = []
    skipped: list[dict[str, object]] = []
    for employee in employees:
        outcome = _create_evaluation_internal(
            db, actor, employee=employee, period=period, kind=kind
        )
        if outcome.evaluation is not None:
            created.append(outcome.evaluation)
        else:
            skipped.append(
                {
                    "employee_id": employee.id,
                    "staff_no": employee.staff_no,
                    "reason": outcome.error_code,
                }
            )
    db.commit()
    return BulkCreateSummary(created=[get_evaluation(db, e.id) for e in created], skipped=skipped)


@dataclass
class ScoreUpdateInput:
    criterion_id: int
    raw_input: Decimal | None
    remarks: str | None = None


def update_evaluation_scores(
    db: Session,
    actor: User,
    evaluation_id: int,
    *,
    expected_row_version: int,
    score_updates: list[ScoreUpdateInput],
    activities: list[str] | None,
) -> Evaluation:
    evaluation = get_evaluation(db, evaluation_id)
    _ensure_period_open(get_period(db, evaluation.period_id))
    if evaluation.status not in (EvaluationStatus.DRAFT.value, EvaluationStatus.RETURNED.value):
        raise bad_request(
            "Evaluation can only be edited while draft or returned", code="evaluation_not_editable"
        )
    if evaluation.owner_user_id != actor.id:
        raise forbidden()
    if evaluation.row_version != expected_row_version:
        raise conflict(
            "This evaluation was changed elsewhere — reload and try again",
            code="row_version_conflict",
        )

    version = db.get(KpiTemplateVersion, evaluation.template_version_id)
    assert version is not None
    criteria_by_id = {c.id: c for c in version.criteria}
    scores_by_criterion = {s.criterion_id: s for s in evaluation.scores}

    for entry in score_updates:
        criterion = criteria_by_id.get(entry.criterion_id)
        score_row = scores_by_criterion.get(entry.criterion_id)
        if criterion is None or score_row is None:
            raise bad_request(
                f"Criterion {entry.criterion_id} does not belong to this evaluation",
                code="invalid_criterion",
            )
        score_row.raw_input = entry.raw_input
        score_row.awarded_marks = (
            awarded_marks_for_input(
                input_mode=criterion.input_mode,
                raw_input=entry.raw_input,
                max_marks=criterion.max_marks,
                allow_negative=criterion.allow_negative,
            )
            if entry.raw_input is not None
            else None
        )
        score_row.remarks = entry.remarks

    if activities is not None:
        evaluation.activities = activities

    _recompute_score(db, evaluation)
    evaluation.row_version += 1
    write_audit(
        db,
        actor_user_id=actor.id,
        action="update_evaluation_scores",
        entity_type="evaluation",
        entity_id=evaluation.id,
        after={"row_version": evaluation.row_version, "score_pct": str(evaluation.score_pct)},
    )
    db.commit()
    return get_evaluation(db, evaluation.id)


def _table_for_kind(kind: str) -> TransitionTable:
    return (
        REGULAR_TRANSITIONS if kind == EvaluationKind.REGULAR.value else SELF_APPRAISAL_TRANSITIONS
    )


def perform_transition(
    db: Session, actor: User, evaluation_id: int, *, action: str, comment: str | None = None
) -> Evaluation:
    evaluation = get_evaluation(db, evaluation_id)
    _ensure_period_open(get_period(db, evaluation.period_id))
    table = _table_for_kind(evaluation.kind)
    # The owner is the other party in every transition except submit (which
    # the owner performs themselves) — good enough without a per-department
    # "assigned manager" concept, which this schema doesn't have.
    notify_user_id = None if action == "submit" else evaluation.owner_user_id
    apply_transition(
        db,
        entity=evaluation,
        entity_type="evaluation",
        table=table,
        action=action,
        actor=actor,
        comment=comment,
        notify_user_id=notify_user_id,
    )
    db.commit()
    return get_evaluation(db, evaluation.id)
