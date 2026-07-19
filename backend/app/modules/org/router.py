from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.enums import RoleCode
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.auth.models import User
from app.modules.org import service
from app.modules.org.models import Position, PositionRate
from app.modules.org.schemas import (
    DepartmentCreateRequest,
    DepartmentOut,
    DepartmentPatchRequest,
    PositionCreateRequest,
    PositionOut,
    PositionPatchRequest,
    PositionRateCreateRequest,
    PositionRateOut,
)

HROnly = Annotated[User, Depends(require_roles(RoleCode.HR))]
RateReaders = Annotated[
    User,
    Depends(require_roles(RoleCode.HR, RoleCode.FINANCE, RoleCode.PMO, RoleCode.ADMIN)),
]

departments_router = APIRouter(prefix="/departments", tags=["org"])
positions_router = APIRouter(prefix="/positions", tags=["org"])


def _rate_to_out(rate: PositionRate) -> PositionRateOut:
    return PositionRateOut(
        id=rate.id,
        position_id=rate.position_id,
        effective_from=rate.effective_from,
        effective_to=rate.effective_to,
        incentive_pct=rate.incentive_pct,
        flat_ref_amount=rate.flat_ref_amount,
    )


def _position_to_out(position: Position, current_rate: PositionRate | None) -> PositionOut:
    return PositionOut(
        id=position.id,
        code=position.code,
        title_en=position.title_en,
        title_ar=position.title_ar,
        is_active=position.is_active,
        current_rate=_rate_to_out(current_rate) if current_rate is not None else None,
    )


@departments_router.get("", response_model=list[DepartmentOut])
def list_departments_endpoint(_user: CurrentUser, db: DbSession) -> list[DepartmentOut]:
    return [
        DepartmentOut(
            id=d.id, code=d.code, name_en=d.name_en, name_ar=d.name_ar, is_active=d.is_active
        )
        for d in service.list_departments(db)
    ]


@departments_router.post("", response_model=DepartmentOut, status_code=201)
def create_department_endpoint(
    payload: DepartmentCreateRequest, actor: HROnly, db: DbSession
) -> DepartmentOut:
    dept = service.create_department(db, actor, payload.code, payload.name_en, payload.name_ar)
    return DepartmentOut(
        id=dept.id, code=dept.code, name_en=dept.name_en, name_ar=dept.name_ar,
        is_active=dept.is_active,
    )


@departments_router.patch("/{department_id}", response_model=DepartmentOut)
def patch_department_endpoint(
    department_id: int, payload: DepartmentPatchRequest, actor: HROnly, db: DbSession
) -> DepartmentOut:
    dept = service.patch_department(
        db,
        actor,
        department_id,
        name_en=payload.name_en,
        name_ar=payload.name_ar,
        is_active=payload.is_active,
    )
    return DepartmentOut(
        id=dept.id, code=dept.code, name_en=dept.name_en, name_ar=dept.name_ar,
        is_active=dept.is_active,
    )


@positions_router.get("", response_model=list[PositionOut])
def list_positions_endpoint(_user: CurrentUser, db: DbSession) -> list[PositionOut]:
    today = date.today()
    return [
        _position_to_out(p, service.rate_as_of(db, p.id, today))
        for p in service.list_positions(db)
    ]


@positions_router.post("", response_model=PositionOut, status_code=201)
def create_position_endpoint(
    payload: PositionCreateRequest, actor: HROnly, db: DbSession
) -> PositionOut:
    position = service.create_position(db, actor, payload.code, payload.title_en, payload.title_ar)
    return _position_to_out(position, None)


@positions_router.patch("/{position_id}", response_model=PositionOut)
def patch_position_endpoint(
    position_id: int, payload: PositionPatchRequest, actor: HROnly, db: DbSession
) -> PositionOut:
    position = service.patch_position(
        db,
        actor,
        position_id,
        title_en=payload.title_en,
        title_ar=payload.title_ar,
        is_active=payload.is_active,
    )
    return _position_to_out(position, service.rate_as_of(db, position.id, date.today()))


@positions_router.get("/{position_id}/rates", response_model=list[PositionRateOut])
def list_position_rates_endpoint(
    position_id: int, _actor: RateReaders, db: DbSession
) -> list[PositionRateOut]:
    return [_rate_to_out(r) for r in service.list_position_rates(db, position_id)]


@positions_router.post("/{position_id}/rates", response_model=PositionRateOut, status_code=201)
def create_position_rate_endpoint(
    position_id: int, payload: PositionRateCreateRequest, actor: HROnly, db: DbSession
) -> PositionRateOut:
    rate = service.create_position_rate(
        db,
        actor,
        position_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        incentive_pct=payload.incentive_pct,
        flat_ref_amount=payload.flat_ref_amount,
    )
    return _rate_to_out(rate)


router = APIRouter()
router.include_router(departments_router)
router.include_router(positions_router)
