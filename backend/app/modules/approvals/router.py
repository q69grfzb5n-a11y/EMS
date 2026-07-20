from fastapi import APIRouter

from app.common.models import ApprovalAction
from app.core.deps import CurrentUser, DbSession
from app.modules.approvals import service
from app.modules.approvals.schemas import ApprovalActionOut, PendingItemOut
from app.modules.evaluations import service as evaluations_service
from app.modules.transfers import service as transfers_service

router = APIRouter(prefix="/approvals", tags=["approvals"])


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


@router.get("/pending", response_model=list[PendingItemOut])
def list_pending_endpoint(user: CurrentUser, db: DbSession) -> list[PendingItemOut]:
    return service.list_pending_for_actor(db, user)


@router.get("/evaluation/{evaluation_id}/history", response_model=list[ApprovalActionOut])
def get_evaluation_history_endpoint(
    evaluation_id: int, _user: CurrentUser, db: DbSession
) -> list[ApprovalActionOut]:
    return [_action_to_out(a) for a in evaluations_service.get_history(db, evaluation_id)]


@router.get("/transfer/{transfer_id}/history", response_model=list[ApprovalActionOut])
def get_transfer_history_endpoint(
    transfer_id: int, _user: CurrentUser, db: DbSession
) -> list[ApprovalActionOut]:
    return [_action_to_out(a) for a in transfers_service.get_history(db, transfer_id)]
