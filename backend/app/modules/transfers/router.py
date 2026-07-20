from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.enums import RoleCode
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.auth.models import User
from app.modules.transfers import service
from app.modules.transfers.models import TransferRequest
from app.modules.transfers.schemas import (
    DepartmentBrief,
    EmployeeBrief,
    TransferCreateRequest,
    TransferRequestOut,
    TransitionRequest,
)

CreateWriters = Annotated[
    User, Depends(require_roles(RoleCode.HR, RoleCode.DEPT_MANAGER, RoleCode.ADMIN))
]

router = APIRouter(prefix="/transfers", tags=["transfers"])


def _transfer_to_out(transfer: TransferRequest) -> TransferRequestOut:
    return TransferRequestOut(
        id=transfer.id,
        employee=EmployeeBrief(
            id=transfer.employee.id,
            staff_no=transfer.employee.staff_no,
            full_name_en=transfer.employee.full_name_en,
            full_name_ar=transfer.employee.full_name_ar,
        ),
        from_department=DepartmentBrief(
            id=transfer.from_department.id,
            code=transfer.from_department.code,
            name_en=transfer.from_department.name_en,
            name_ar=transfer.from_department.name_ar,
        ),
        to_department=DepartmentBrief(
            id=transfer.to_department.id,
            code=transfer.to_department.code,
            name_en=transfer.to_department.name_en,
            name_ar=transfer.to_department.name_ar,
        ),
        effective_date=transfer.effective_date,
        reason=transfer.reason,
        status=transfer.status,
        requested_by_user_id=transfer.requested_by_user_id,
    )


@router.get("", response_model=list[TransferRequestOut])
def list_transfers_endpoint(user: CurrentUser, db: DbSession) -> list[TransferRequestOut]:
    return [_transfer_to_out(t) for t in service.list_transfers_scoped(db, user)]


@router.post("", response_model=TransferRequestOut, status_code=201)
def create_transfer_endpoint(
    payload: TransferCreateRequest, actor: CreateWriters, db: DbSession
) -> TransferRequestOut:
    transfer = service.create_transfer(
        db,
        actor,
        employee_id=payload.employee_id,
        to_department_id=payload.to_department_id,
        effective_date=payload.effective_date,
        reason=payload.reason,
    )
    return _transfer_to_out(transfer)


@router.get("/{transfer_id}", response_model=TransferRequestOut)
def get_transfer_endpoint(transfer_id: int, user: CurrentUser, db: DbSession) -> TransferRequestOut:
    return _transfer_to_out(service.get_transfer_scoped(db, user, transfer_id))


@router.post("/{transfer_id}/submit", response_model=TransferRequestOut)
def submit_transfer_endpoint(
    transfer_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> TransferRequestOut:
    transfer = service.perform_transition(
        db, actor, transfer_id, action="submit", comment=payload.comment
    )
    return _transfer_to_out(transfer)


@router.post("/{transfer_id}/review", response_model=TransferRequestOut)
def review_transfer_endpoint(
    transfer_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> TransferRequestOut:
    transfer = service.perform_transition(
        db, actor, transfer_id, action="review", comment=payload.comment
    )
    return _transfer_to_out(transfer)


@router.post("/{transfer_id}/approve", response_model=TransferRequestOut)
def approve_transfer_endpoint(
    transfer_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> TransferRequestOut:
    transfer = service.perform_transition(
        db, actor, transfer_id, action="approve", comment=payload.comment
    )
    return _transfer_to_out(transfer)


@router.post("/{transfer_id}/return", response_model=TransferRequestOut)
def return_transfer_endpoint(
    transfer_id: int, payload: TransitionRequest, actor: CurrentUser, db: DbSession
) -> TransferRequestOut:
    transfer = service.perform_transition(
        db, actor, transfer_id, action="return", comment=payload.comment
    )
    return _transfer_to_out(transfer)
