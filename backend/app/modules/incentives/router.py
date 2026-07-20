from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.enums import RoleCode
from app.common.models import ApprovalAction
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.approvals.schemas import ApprovalActionOut
from app.modules.auth.models import User
from app.modules.incentives import service
from app.modules.incentives.models import IncentiveLineItem, IncentiveRun
from app.modules.incentives.schemas import (
    DepartmentBrief,
    EmployeeBrief,
    ExceptionOut,
    IncentiveLineItemOut,
    IncentiveRunOut,
    LineUpdateRequest,
    RunCreateRequest,
    TransitionRequest,
)
from app.modules.incentives.service import LineUpdateInput

RunWriters = Annotated[User, Depends(require_roles(RoleCode.HR, RoleCode.PMO, RoleCode.ADMIN))]

router = APIRouter(prefix="/incentive-runs", tags=["incentives"])


def _employee_brief(line: IncentiveLineItem) -> EmployeeBrief:
    employee = line.employee
    department = employee.department
    return EmployeeBrief(
        id=employee.id,
        staff_no=employee.staff_no,
        full_name_en=employee.full_name_en,
        full_name_ar=employee.full_name_ar,
        department=DepartmentBrief(
            id=department.id,
            code=department.code,
            name_en=department.name_en,
            name_ar=department.name_ar,
        ),
    )


def _line_to_out(line: IncentiveLineItem) -> IncentiveLineItemOut:
    return IncentiveLineItemOut(
        id=line.id,
        employee=_employee_brief(line),
        evaluation_id=line.evaluation_id,
        evaluation_pct=line.evaluation_pct,
        formula_mode=line.formula_mode,
        flat_ref_amount=line.flat_ref_amount,
        base_salary=line.base_salary,
        position_incentive_pct=line.position_incentive_pct,
        attendance_factor=line.attendance_factor,
        target_ratio=line.target_ratio,
        computed_amount=line.computed_amount,
        override_amount=line.override_amount,
        override_reason=line.override_reason,
        final_amount=line.final_amount,
        is_excluded=line.is_excluded,
        exclude_reason=line.exclude_reason,
        row_version=line.row_version,
    )


def _run_to_out(run: IncentiveRun, lines: list[IncentiveLineItem] | None = None) -> IncentiveRunOut:
    visible_lines = run.lines if lines is None else lines
    total = sum((line.final_amount for line in run.lines if not line.is_excluded), Decimal(0))
    return IncentiveRunOut(
        id=run.id,
        period_id=run.period_id,
        run_no=run.run_no,
        status=run.status,
        params=run.params,
        exceptions=[ExceptionOut(**e) for e in run.exceptions],
        created_by_user_id=run.created_by_user_id,
        total_final_amount=total,
        lines=[_line_to_out(line) for line in visible_lines],
    )


def _action_to_out(action: ApprovalAction) -> ApprovalActionOut:
    return ApprovalActionOut(
        id=action.id,
        entity_type=action.entity_type,
        entity_id=action.entity_id,
        action=action.action,
        from_status=action.from_status,
        to_status=action.to_status,
        actor_user_id=action.actor_user_id,
        actor_role=action.actor_role,
        comment=action.comment,
        created_at=action.created_at,
    )


@router.get("", response_model=list[IncentiveRunOut])
def list_runs_endpoint(
    _user: CurrentUser, db: DbSession, period_id: int | None = None
) -> list[IncentiveRunOut]:
    return [_run_to_out(r) for r in service.list_runs(db, period_id=period_id)]


@router.post("", response_model=IncentiveRunOut, status_code=201)
def create_run_endpoint(
    payload: RunCreateRequest, actor: RunWriters, db: DbSession
) -> IncentiveRunOut:
    run = service.create_run(
        db,
        actor,
        period_id=payload.period_id,
        formula_mode=payload.formula_mode,
        rounding_step=payload.rounding_step,
        rounding_mode=payload.rounding_mode,
    )
    return _run_to_out(run)


@router.get("/{run_id}", response_model=IncentiveRunOut)
def get_run_endpoint(run_id: int, user: CurrentUser, db: DbSession) -> IncentiveRunOut:
    run = service.get_run(db, run_id)
    lines = service.list_lines_scoped(db, user, run_id)
    return _run_to_out(run, lines=lines)


@router.post("/{run_id}/recalculate", response_model=IncentiveRunOut)
def recalculate_run_endpoint(run_id: int, actor: RunWriters, db: DbSession) -> IncentiveRunOut:
    run = service.recalculate_run(db, actor, run_id)
    return _run_to_out(run)


@router.patch("/{run_id}/lines/{line_id}", response_model=IncentiveRunOut)
def update_line_endpoint(
    run_id: int, line_id: int, payload: LineUpdateRequest, actor: RunWriters, db: DbSession
) -> IncentiveRunOut:
    run = service.update_line(
        db,
        actor,
        run_id,
        line_id,
        expected_row_version=payload.row_version,
        updates=LineUpdateInput(
            attendance_factor=payload.attendance_factor,
            override_amount=payload.override_amount,
            override_reason=payload.override_reason,
            clear_override=payload.clear_override,
            is_excluded=payload.is_excluded,
            exclude_reason=payload.exclude_reason,
        ),
    )
    return _run_to_out(run)


@router.post("/{run_id}/submit-audit", response_model=IncentiveRunOut)
def submit_audit_endpoint(
    run_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> IncentiveRunOut:
    run = service.perform_transition(
        db, actor, run_id, action="submit_audit", comment=payload.comment
    )
    return _run_to_out(run)


@router.post("/{run_id}/complete-audit", response_model=IncentiveRunOut)
def complete_audit_endpoint(
    run_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> IncentiveRunOut:
    run = service.perform_transition(
        db, actor, run_id, action="complete_audit", comment=payload.comment
    )
    return _run_to_out(run)


@router.post("/{run_id}/approve", response_model=IncentiveRunOut)
def approve_run_endpoint(
    run_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> IncentiveRunOut:
    run = service.perform_transition(db, actor, run_id, action="approve", comment=payload.comment)
    return _run_to_out(run)


@router.post("/{run_id}/reject", response_model=IncentiveRunOut)
def reject_run_endpoint(
    run_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> IncentiveRunOut:
    run = service.perform_transition(db, actor, run_id, action="reject", comment=payload.comment)
    return _run_to_out(run)


@router.get("/{run_id}/history", response_model=list[ApprovalActionOut])
def get_run_history_endpoint(
    run_id: int, _user: CurrentUser, db: DbSession
) -> list[ApprovalActionOut]:
    return [_action_to_out(a) for a in service.get_history(db, run_id)]


@router.get("/my/incentives", response_model=list[IncentiveLineItemOut])
def list_my_incentives_endpoint(user: CurrentUser, db: DbSession) -> list[IncentiveLineItemOut]:
    return [_line_to_out(line) for line in service.list_my_incentives(db, user)]
