from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import write_audit
from app.common.errors import bad_request, conflict, not_found
from app.modules.auth.models import User
from app.modules.org.models import Department, Position, PositionRate


def list_departments(db: Session, *, include_inactive: bool = True) -> list[Department]:
    stmt = select(Department).order_by(Department.code)
    if not include_inactive:
        stmt = stmt.where(Department.is_active.is_(True))
    return list(db.scalars(stmt))


def get_department(db: Session, department_id: int) -> Department:
    dept = db.get(Department, department_id)
    if dept is None:
        raise not_found("Department not found")
    return dept


def create_department(
    db: Session, actor: User, code: str, name_en: str, name_ar: str
) -> Department:
    if db.scalars(select(Department).where(Department.code == code)).first() is not None:
        raise conflict("A department with this code already exists", code="department_code_taken")

    dept = Department(code=code, name_en=name_en, name_ar=name_ar, is_active=True)
    db.add(dept)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_department",
        entity_type="department",
        entity_id=dept.id,
        after={"code": code, "name_en": name_en, "name_ar": name_ar},
    )
    db.commit()
    return dept


def patch_department(
    db: Session,
    actor: User,
    department_id: int,
    *,
    name_en: str | None,
    name_ar: str | None,
    is_active: bool | None,
) -> Department:
    dept = get_department(db, department_id)
    before = {"name_en": dept.name_en, "name_ar": dept.name_ar, "is_active": dept.is_active}
    if name_en is not None:
        dept.name_en = name_en
    if name_ar is not None:
        dept.name_ar = name_ar
    if is_active is not None:
        dept.is_active = is_active
    write_audit(
        db,
        actor_user_id=actor.id,
        action="patch_department",
        entity_type="department",
        entity_id=dept.id,
        before=before,
        after={"name_en": dept.name_en, "name_ar": dept.name_ar, "is_active": dept.is_active},
    )
    db.commit()
    return dept


def list_positions(db: Session, *, include_inactive: bool = True) -> list[Position]:
    stmt = select(Position).order_by(Position.code)
    if not include_inactive:
        stmt = stmt.where(Position.is_active.is_(True))
    return list(db.scalars(stmt))


def get_position(db: Session, position_id: int) -> Position:
    position = db.get(Position, position_id)
    if position is None:
        raise not_found("Position not found")
    return position


def create_position(
    db: Session, actor: User, code: str, title_en: str, title_ar: str
) -> Position:
    if db.scalars(select(Position).where(Position.code == code)).first() is not None:
        raise conflict("A position with this code already exists", code="position_code_taken")

    position = Position(code=code, title_en=title_en, title_ar=title_ar, is_active=True)
    db.add(position)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_position",
        entity_type="position",
        entity_id=position.id,
        after={"code": code, "title_en": title_en, "title_ar": title_ar},
    )
    db.commit()
    return position


def patch_position(
    db: Session,
    actor: User,
    position_id: int,
    *,
    title_en: str | None,
    title_ar: str | None,
    is_active: bool | None,
) -> Position:
    position = get_position(db, position_id)
    before = {
        "title_en": position.title_en,
        "title_ar": position.title_ar,
        "is_active": position.is_active,
    }
    if title_en is not None:
        position.title_en = title_en
    if title_ar is not None:
        position.title_ar = title_ar
    if is_active is not None:
        position.is_active = is_active
    write_audit(
        db,
        actor_user_id=actor.id,
        action="patch_position",
        entity_type="position",
        entity_id=position.id,
        before=before,
        after={
            "title_en": position.title_en,
            "title_ar": position.title_ar,
            "is_active": position.is_active,
        },
    )
    db.commit()
    return position


def rate_as_of(db: Session, position_id: int, as_of: date) -> PositionRate | None:
    """First-day-of-month rule: caller passes the first day of the relevant month."""
    stmt = select(PositionRate).where(
        PositionRate.position_id == position_id,
        PositionRate.effective_from <= as_of,
        (PositionRate.effective_to.is_(None)) | (PositionRate.effective_to > as_of),
    )
    return db.scalars(stmt).first()


def list_position_rates(db: Session, position_id: int) -> list[PositionRate]:
    get_position(db, position_id)  # 404 if missing
    stmt = (
        select(PositionRate)
        .where(PositionRate.position_id == position_id)
        .order_by(PositionRate.effective_from.desc())
    )
    return list(db.scalars(stmt))


def create_position_rate(
    db: Session,
    actor: User,
    position_id: int,
    *,
    effective_from: date,
    effective_to: date | None,
    incentive_pct: Decimal | None,
    flat_ref_amount: Decimal | None,
) -> PositionRate:
    get_position(db, position_id)  # 404 if missing
    if effective_to is not None and effective_to <= effective_from:
        raise bad_request("effective_to must be after effective_from", code="invalid_date_range")

    rate = PositionRate(
        position_id=position_id,
        effective_from=effective_from,
        effective_to=effective_to,
        incentive_pct=incentive_pct,
        flat_ref_amount=flat_ref_amount,
    )
    db.add(rate)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise conflict(
            "This date range overlaps an existing rate window for the position",
            code="rate_overlap",
        ) from exc

    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_position_rate",
        entity_type="position_rate",
        entity_id=rate.id,
        after={
            "position_id": position_id,
            "effective_from": str(effective_from),
            "effective_to": str(effective_to) if effective_to else None,
            "incentive_pct": str(incentive_pct) if incentive_pct is not None else None,
            "flat_ref_amount": str(flat_ref_amount) if flat_ref_amount is not None else None,
        },
    )
    db.commit()
    return rate
