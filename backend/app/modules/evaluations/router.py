from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.enums import RoleCode
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.auth.models import User
from app.modules.evaluations import service
from app.modules.evaluations.models import Evaluation, EvaluationScore
from app.modules.evaluations.schemas import (
    BulkCreateRequest,
    BulkCreateResponse,
    BulkCreateSkipped,
    EmployeeBrief,
    EvaluationCreateRequest,
    EvaluationOut,
    EvaluationScoreOut,
    EvaluationUpdateRequest,
    SelfAppraisalCreateRequest,
    TransitionRequest,
)
from app.modules.evaluations.service import ScoreUpdateInput

CreateWriters = Annotated[User, Depends(require_roles(RoleCode.HR, RoleCode.PMO, RoleCode.ADMIN))]

evaluations_router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _score_to_out(score: EvaluationScore) -> EvaluationScoreOut:
    criterion = score.criterion
    return EvaluationScoreOut(
        criterion_id=score.criterion_id,
        name_en=criterion.name_en,
        name_ar=criterion.name_ar,
        guidance_en=criterion.guidance_en,
        guidance_ar=criterion.guidance_ar,
        max_marks=criterion.max_marks,
        input_mode=criterion.input_mode,
        allow_negative=criterion.allow_negative,
        raw_input=score.raw_input,
        awarded_marks=score.awarded_marks,
        auto_suggested_marks=score.auto_suggested_marks,
        remarks=score.remarks,
    )


def _evaluation_to_out(evaluation: Evaluation) -> EvaluationOut:
    scores_sorted = sorted(evaluation.scores, key=lambda s: s.criterion.sort_order)
    return EvaluationOut(
        id=evaluation.id,
        employee=EmployeeBrief(
            id=evaluation.employee.id,
            staff_no=evaluation.employee.staff_no,
            full_name_en=evaluation.employee.full_name_en,
            full_name_ar=evaluation.employee.full_name_ar,
        ),
        period_id=evaluation.period_id,
        kind=evaluation.kind,
        status=evaluation.status,
        template_version_id=evaluation.template_version_id,
        owner_user_id=evaluation.owner_user_id,
        activities=evaluation.activities,
        score_pct=evaluation.score_pct,
        grade=evaluation.grade,
        row_version=evaluation.row_version,
        scores=[_score_to_out(s) for s in scores_sorted],
    )


@evaluations_router.get("", response_model=list[EvaluationOut])
def list_evaluations_endpoint(
    user: CurrentUser, db: DbSession, period_id: int | None = None
) -> list[EvaluationOut]:
    return [
        _evaluation_to_out(e)
        for e in service.list_evaluations_scoped(db, user, period_id=period_id)
    ]


@evaluations_router.post("", response_model=EvaluationOut, status_code=201)
def create_evaluation_endpoint(
    payload: EvaluationCreateRequest, actor: CreateWriters, db: DbSession
) -> EvaluationOut:
    evaluation = service.create_evaluation(
        db, actor, employee_id=payload.employee_id, period_id=payload.period_id, kind=payload.kind
    )
    return _evaluation_to_out(evaluation)


@evaluations_router.post("/self", response_model=EvaluationOut, status_code=201)
def create_self_appraisal_endpoint(
    payload: SelfAppraisalCreateRequest, actor: CurrentUser, db: DbSession
) -> EvaluationOut:
    evaluation = service.create_self_appraisal(db, actor, period_id=payload.period_id)
    return _evaluation_to_out(evaluation)


@evaluations_router.post("/bulk", response_model=BulkCreateResponse, status_code=201)
def bulk_create_evaluations_endpoint(
    payload: BulkCreateRequest, actor: CreateWriters, db: DbSession
) -> BulkCreateResponse:
    summary = service.bulk_create_evaluations(
        db,
        actor,
        department_id=payload.department_id,
        period_id=payload.period_id,
        kind=payload.kind,
    )
    return BulkCreateResponse(
        created=[_evaluation_to_out(e) for e in summary.created],
        skipped=[BulkCreateSkipped(**s) for s in summary.skipped],  # type: ignore[arg-type]
    )


@evaluations_router.get("/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation_endpoint(evaluation_id: int, user: CurrentUser, db: DbSession) -> EvaluationOut:
    return _evaluation_to_out(service.get_evaluation_scoped(db, user, evaluation_id))


@evaluations_router.patch("/{evaluation_id}", response_model=EvaluationOut)
def update_evaluation_endpoint(
    evaluation_id: int, payload: EvaluationUpdateRequest, actor: CurrentUser, db: DbSession
) -> EvaluationOut:
    evaluation = service.update_evaluation_scores(
        db,
        actor,
        evaluation_id,
        expected_row_version=payload.row_version,
        score_updates=[
            ScoreUpdateInput(criterion_id=s.criterion_id, raw_input=s.raw_input, remarks=s.remarks)
            for s in payload.scores
        ],
        activities=payload.activities,
    )
    return _evaluation_to_out(evaluation)


@evaluations_router.post("/{evaluation_id}/submit", response_model=EvaluationOut)
def submit_evaluation_endpoint(
    evaluation_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> EvaluationOut:
    evaluation = service.perform_transition(
        db, actor, evaluation_id, action="submit", comment=payload.comment
    )
    return _evaluation_to_out(evaluation)


@evaluations_router.post("/{evaluation_id}/approve", response_model=EvaluationOut)
def approve_evaluation_endpoint(
    evaluation_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> EvaluationOut:
    evaluation = service.perform_transition(
        db, actor, evaluation_id, action="approve", comment=payload.comment
    )
    return _evaluation_to_out(evaluation)


@evaluations_router.post("/{evaluation_id}/return", response_model=EvaluationOut)
def return_evaluation_endpoint(
    evaluation_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> EvaluationOut:
    evaluation = service.perform_transition(
        db, actor, evaluation_id, action="return", comment=payload.comment
    )
    return _evaluation_to_out(evaluation)


@evaluations_router.post("/{evaluation_id}/review", response_model=EvaluationOut)
def review_evaluation_endpoint(
    evaluation_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> EvaluationOut:
    evaluation = service.perform_transition(
        db, actor, evaluation_id, action="review", comment=payload.comment
    )
    return _evaluation_to_out(evaluation)
