from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.common.audit import write_audit
from app.common.enums import (
    EmploymentStatus,
    EvaluationStatus,
    IncentiveRunStatus,
    PeriodStatus,
    RoleCode,
)
from app.common.errors import bad_request, conflict, forbidden, not_found
from app.common.models import ApprovalAction
from app.common.workflow import apply_transition, transition_history
from app.modules.attendance.models import AttendanceRecord, IncentivePeriod
from app.modules.attendance.service import get_period
from app.modules.auth.models import User
from app.modules.employees.models import Employee
from app.modules.employees.service import salary_as_of
from app.modules.evaluations.models import Evaluation
from app.modules.incentives.engine import FORMULA_MODES, LEGACY_FLAT, LineInputs, compute_line
from app.modules.incentives.engine import RunParams as EngineRunParams
from app.modules.incentives.models import IncentiveLineItem, IncentiveRun
from app.modules.incentives.workflow import RUN_TRANSITIONS
from app.modules.org.service import rate_as_of

# Roles with unrestricted visibility across every run. Shares HR/ADMIN/PMO/
# FACTORY_MANAGER with evaluations/transfers, plus FINANCE — who already has
# export rights over this exact data via reports.router's FinanceReaders —
# so they aren't scoped out of viewing/listing runs through the API instead.
FULL_ACCESS_ROLES = {
    RoleCode.HR.value,
    RoleCode.ADMIN.value,
    RoleCode.PMO.value,
    RoleCode.FACTORY_MANAGER.value,
    RoleCode.FINANCE.value,
}
# An evaluation counts toward a run once it has reached either kind's terminal
# approved status (REGULAR ends at manager_approved, SELF_APPRAISAL at fm_approved).
APPROVED_EVAL_STATUSES = {
    EvaluationStatus.MANAGER_APPROVED.value,
    EvaluationStatus.FM_APPROVED.value,
}


def _actor_department_id(db: Session, actor: User) -> int | None:
    if actor.employee_id is None:
        return None
    employee = db.get(Employee, actor.employee_id)
    return employee.department_id if employee is not None else None


def _run_query() -> Select[tuple[IncentiveRun]]:
    return select(IncentiveRun).options(
        selectinload(IncentiveRun.lines)
        .selectinload(IncentiveLineItem.employee)
        .selectinload(Employee.department)
    )


def get_run(db: Session, run_id: int) -> IncentiveRun:
    run = db.scalars(_run_query().where(IncentiveRun.id == run_id)).first()
    if run is None:
        raise not_found("Incentive run not found")
    return run


def get_approved_run_for_period(db: Session, period_id: int) -> IncentiveRun | None:
    """Used by the reports module — the one approved run for a period, if any."""
    stmt = _run_query().where(
        IncentiveRun.period_id == period_id,
        IncentiveRun.status == IncentiveRunStatus.APPROVED.value,
    )
    return db.scalars(stmt).first()


def list_runs(db: Session, *, period_id: int | None = None) -> list[IncentiveRun]:
    stmt = _run_query().order_by(IncentiveRun.id.desc())
    if period_id is not None:
        stmt = stmt.where(IncentiveRun.period_id == period_id)
    return list(db.scalars(stmt))


def _scope_lines(db: Session, actor: User, run: IncentiveRun) -> list[IncentiveLineItem] | None:
    """None means the actor has no visibility into this run at all — distinct
    from an empty list, which means visibility but nothing in scope."""
    role_codes = set(actor.role_codes)
    if FULL_ACCESS_ROLES.intersection(role_codes):
        return run.lines
    if RoleCode.DEPT_MANAGER.value in role_codes:
        dept_id = _actor_department_id(db, actor)
        if dept_id is None:
            return None
        return [line for line in run.lines if line.employee.department_id == dept_id]
    return None


def scope_lines_or_forbidden(
    db: Session, actor: User, run: IncentiveRun
) -> list[IncentiveLineItem]:
    """Like _scope_lines, but for a caller that already has the run loaded —
    avoids re-fetching it just to re-derive the same scoping decision."""
    lines = _scope_lines(db, actor, run)
    if lines is None:
        raise forbidden()
    return lines


def list_lines_scoped(db: Session, actor: User, run_id: int) -> list[IncentiveLineItem]:
    run = get_run(db, run_id)
    return scope_lines_or_forbidden(db, actor, run)


def list_runs_scoped(
    db: Session, actor: User, *, period_id: int | None = None
) -> list[tuple[IncentiveRun, list[IncentiveLineItem]]]:
    """Each run paired with the actor's visible lines; a run the actor cannot see
    at all is omitted entirely — the list endpoint must not bypass the same
    scoping the single-run detail endpoint already enforces."""
    pairs = []
    for run in list_runs(db, period_id=period_id):
        lines = _scope_lines(db, actor, run)
        if lines is not None:
            pairs.append((run, lines))
    return pairs


def get_history(db: Session, run_id: int) -> list[ApprovalAction]:
    get_run(db, run_id)  # 404 if missing
    return transition_history(db, entity_type="incentive_run", entity_id=run_id)


def list_my_incentives(db: Session, actor: User) -> list[IncentiveLineItem]:
    if actor.employee_id is None:
        return []
    stmt = (
        select(IncentiveLineItem)
        .join(IncentiveRun, IncentiveRun.id == IncentiveLineItem.run_id)
        .where(
            IncentiveLineItem.employee_id == actor.employee_id,
            IncentiveRun.status == IncentiveRunStatus.APPROVED.value,
        )
        .options(selectinload(IncentiveLineItem.employee))
    )
    return list(db.scalars(stmt))


# ---- run creation: resolve every employee, exceptions transparently reported ----


@dataclass
class _ResolvedLine:
    evaluation_id: int
    evaluation_pct: Decimal
    flat_ref_amount: Decimal | None
    base_salary: Decimal | None
    position_incentive_pct: Decimal | None


@dataclass
class _ResolveOutcome:
    line: "_ResolvedLine | None"
    exception_reason: str | None


def _latest_approved_evaluation(db: Session, employee_id: int, period_id: int) -> Evaluation | None:
    stmt = (
        select(Evaluation)
        .where(
            Evaluation.employee_id == employee_id,
            Evaluation.period_id == period_id,
            Evaluation.status.in_(APPROVED_EVAL_STATUSES),
        )
        .order_by(Evaluation.created_at.desc())
    )
    return db.scalars(stmt).first()


def _resolve_employee_line(
    db: Session, employee: Employee, period: IncentivePeriod, *, formula_mode: str, as_of: date
) -> _ResolveOutcome:
    if employee.employment_status != EmploymentStatus.ACTIVE.value:
        return _ResolveOutcome(None, "inactive")

    evaluation = _latest_approved_evaluation(db, employee.id, period.id)
    if evaluation is None:
        return _ResolveOutcome(None, "missing_evaluation")

    attendance = db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee.id, AttendanceRecord.period_id == period.id
        )
    ).first()
    if attendance is None:
        return _ResolveOutcome(None, "missing_attendance")

    flat_ref_amount: Decimal | None = None
    base_salary: Decimal | None = None
    position_incentive_pct: Decimal | None = None

    if formula_mode == LEGACY_FLAT:
        rate = rate_as_of(db, employee.position_id, as_of)
        if rate is None or rate.flat_ref_amount is None:
            return _ResolveOutcome(None, "missing_position_rate")
        flat_ref_amount = rate.flat_ref_amount
    else:
        salary = salary_as_of(db, employee.id, as_of)
        if salary is None:
            return _ResolveOutcome(None, "missing_salary")
        rate = rate_as_of(db, employee.position_id, as_of)
        if rate is None or rate.incentive_pct is None:
            return _ResolveOutcome(None, "missing_position_rate")
        base_salary = salary.base_salary
        position_incentive_pct = rate.incentive_pct

    return _ResolveOutcome(
        _ResolvedLine(
            evaluation_id=evaluation.id,
            evaluation_pct=evaluation.score_pct or Decimal(0),
            flat_ref_amount=flat_ref_amount,
            base_salary=base_salary,
            position_incentive_pct=position_incentive_pct,
        ),
        None,
    )


def _next_run_no(db: Session, period_id: int) -> int:
    max_no = db.scalar(
        select(func.max(IncentiveRun.run_no)).where(IncentiveRun.period_id == period_id)
    )
    return (max_no or 0) + 1


def create_run(
    db: Session,
    actor: User,
    *,
    period_id: int,
    formula_mode: str,
    rounding_step: Decimal = Decimal(10),
    rounding_mode: str = "CEILING",
) -> IncentiveRun:
    if formula_mode not in FORMULA_MODES:
        raise bad_request("Unknown formula mode", code="invalid_formula_mode")

    period = get_period(db, period_id)
    if period.target_pool is None or period.actual_pool is None:
        raise bad_request(
            "Set the period's target and actual pool figures before creating a run",
            code="pools_not_set",
        )
    if period.target_pool == 0:
        raise bad_request("Target pool cannot be zero", code="invalid_target_pool")

    target_ratio = period.actual_pool / period.target_pool
    as_of = date(period.year, period.month, 1)
    engine_params = EngineRunParams(rounding_step=rounding_step, rounding_mode=rounding_mode)

    run = IncentiveRun(
        period_id=period.id,
        run_no=_next_run_no(db, period.id),
        params={
            "formula_mode": formula_mode,
            "rounding_step": str(rounding_step),
            "rounding_mode": rounding_mode,
            "engine_version": "v1",
        },
        exceptions=[],
        created_by_user_id=actor.id,
    )
    db.add(run)
    db.flush()

    # Every employee, active or not, so "inactive" is a visible, explained
    # exception rather than a silent filter — same philosophy as Phase 5's
    # bulk_create_evaluations.
    employees = list(db.scalars(select(Employee).order_by(Employee.id)))
    exceptions: list[dict[str, object]] = []
    line_count = 0

    for employee in employees:
        outcome = _resolve_employee_line(
            db, employee, period, formula_mode=formula_mode, as_of=as_of
        )
        if outcome.line is None:
            exceptions.append(
                {
                    "employee_id": employee.id,
                    "staff_no": employee.staff_no,
                    "reason": outcome.exception_reason,
                }
            )
            continue

        resolved = outcome.line
        result = compute_line(
            LineInputs(
                evaluation_pct=resolved.evaluation_pct,
                formula_mode=formula_mode,
                flat_ref_amount=resolved.flat_ref_amount,
                base_salary=resolved.base_salary,
                position_incentive_pct=resolved.position_incentive_pct,
                attendance_factor=Decimal("1.00"),
                target_ratio=target_ratio,
            ),
            engine_params,
        )
        db.add(
            IncentiveLineItem(
                run_id=run.id,
                employee_id=employee.id,
                evaluation_id=resolved.evaluation_id,
                evaluation_pct=resolved.evaluation_pct,
                formula_mode=formula_mode,
                flat_ref_amount=resolved.flat_ref_amount,
                base_salary=resolved.base_salary,
                position_incentive_pct=resolved.position_incentive_pct,
                attendance_factor=Decimal("1.00"),
                target_ratio=target_ratio,
                computed_amount=result.computed_amount,
                final_amount=result.computed_amount,
            )
        )
        line_count += 1

    run.exceptions = exceptions
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_incentive_run",
        entity_type="incentive_run",
        entity_id=run.id,
        after={
            "period_id": period.id,
            "run_no": run.run_no,
            "formula_mode": formula_mode,
            "lines": line_count,
            "exceptions": len(exceptions),
        },
    )
    db.commit()
    return get_run(db, run.id)


# ---- draft-only editing: recalculate, per-line PATCH ----------------------


def _engine_params_from_run(run: IncentiveRun) -> EngineRunParams:
    return EngineRunParams(
        rounding_step=Decimal(str(run.params["rounding_step"])),
        rounding_mode=run.params["rounding_mode"],
    )


def _recompute_line(
    line: IncentiveLineItem, *, formula_mode: str, engine_params: EngineRunParams
) -> None:
    result = compute_line(
        LineInputs(
            evaluation_pct=line.evaluation_pct,
            formula_mode=formula_mode,
            flat_ref_amount=line.flat_ref_amount,
            base_salary=line.base_salary,
            position_incentive_pct=line.position_incentive_pct,
            attendance_factor=line.attendance_factor,
            target_ratio=line.target_ratio,
        ),
        engine_params,
    )
    line.computed_amount = result.computed_amount
    if line.override_amount is None:
        line.final_amount = result.computed_amount


def recalculate_run(db: Session, actor: User, run_id: int) -> IncentiveRun:
    run = get_run(db, run_id)
    if run.status != IncentiveRunStatus.DRAFT.value:
        raise bad_request("Only a draft run can be recalculated", code="run_not_draft")

    engine_params = _engine_params_from_run(run)
    formula_mode = run.params["formula_mode"]
    for line in run.lines:
        if line.is_excluded:
            continue
        _recompute_line(line, formula_mode=formula_mode, engine_params=engine_params)
        line.row_version += 1

    write_audit(
        db,
        actor_user_id=actor.id,
        action="recalculate_incentive_run",
        entity_type="incentive_run",
        entity_id=run.id,
    )
    db.commit()
    return get_run(db, run.id)


@dataclass
class LineUpdateInput:
    attendance_factor: Decimal | None = None
    override_amount: Decimal | None = None
    override_reason: str | None = None
    clear_override: bool = False
    is_excluded: bool | None = None
    exclude_reason: str | None = None


def update_line(
    db: Session,
    actor: User,
    run_id: int,
    line_id: int,
    *,
    expected_row_version: int,
    updates: LineUpdateInput,
) -> IncentiveRun:
    run = get_run(db, run_id)
    if run.status != IncentiveRunStatus.DRAFT.value:
        raise bad_request("Lines can only be edited while the run is a draft", code="run_not_draft")

    line = next((line for line in run.lines if line.id == line_id), None)
    if line is None:
        raise not_found("Line item not found")
    if line.row_version != expected_row_version:
        raise conflict(
            "This line was changed elsewhere — reload and try again", code="row_version_conflict"
        )

    if updates.attendance_factor is not None:
        line.attendance_factor = updates.attendance_factor

    if updates.clear_override:
        line.override_amount = None
        line.override_reason = None
    elif updates.override_amount is not None:
        if not updates.override_reason:
            raise bad_request("An override requires a reason", code="override_reason_required")
        line.override_amount = updates.override_amount
        line.override_reason = updates.override_reason

    if updates.is_excluded is not None:
        if updates.is_excluded and not updates.exclude_reason:
            raise bad_request("Excluding a line requires a reason", code="exclude_reason_required")
        line.is_excluded = updates.is_excluded
        line.exclude_reason = updates.exclude_reason if updates.is_excluded else None

    engine_params = _engine_params_from_run(run)
    _recompute_line(line, formula_mode=run.params["formula_mode"], engine_params=engine_params)
    if line.override_amount is not None:
        line.final_amount = line.override_amount
    line.row_version += 1

    write_audit(
        db,
        actor_user_id=actor.id,
        action="update_incentive_line",
        entity_type="incentive_line_item",
        entity_id=line.id,
        after={"final_amount": str(line.final_amount), "is_excluded": line.is_excluded},
    )
    db.commit()
    return get_run(db, run.id)


# ---- workflow transitions + period lock ------------------------------------


def perform_transition(
    db: Session, actor: User, run_id: int, *, action: str, comment: str | None = None
) -> IncentiveRun:
    run = get_run(db, run_id)
    if action == "submit_audit" and not run.lines:
        raise bad_request("This run has no line items to submit", code="run_has_no_lines")

    try:
        apply_transition(
            db,
            entity=run,
            entity_type="incentive_run",
            table=RUN_TRANSITIONS,
            action=action,
            actor=actor,
            comment=comment,
        )
    except IntegrityError as exc:
        db.rollback()
        raise conflict(
            "This period already has an approved incentive run",
            code="period_already_has_approved_run",
        ) from exc

    if action == "approve":
        period = get_period(db, run.period_id)
        period.status = PeriodStatus.LOCKED.value
        write_audit(
            db,
            actor_user_id=actor.id,
            action="lock_period_via_run_approval",
            entity_type="incentive_period",
            entity_id=period.id,
        )

    db.commit()
    return get_run(db, run.id)
