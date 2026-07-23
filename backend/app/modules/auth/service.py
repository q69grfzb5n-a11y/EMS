from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.common.audit import write_audit
from app.common.errors import bad_request, conflict, not_found, unauthorized
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth.models import RefreshToken, Role, User, UserRole

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def _user_with_roles_query() -> Select[tuple[User]]:
    return select(User).options(selectinload(User.user_roles).selectinload(UserRole.role))


def get_user_by_staff_no(db: Session, staff_no: str) -> User | None:
    stmt = _user_with_roles_query().where(User.staff_no == staff_no)
    return db.scalars(stmt).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    stmt = _user_with_roles_query().where(User.id == user_id)
    return db.scalars(stmt).first()


_INVALID_CREDENTIALS_MESSAGE = "Invalid staff number or password"
_ACCOUNT_LOCKED_MESSAGE = (
    "Account temporarily locked after repeated failed logins. Try again later."
)


def authenticate(db: Session, staff_no: str, password: str) -> User:
    user = get_user_by_staff_no(db, staff_no)
    if user is None or not user.is_active:
        raise unauthorized(_INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")

    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until.replace(tzinfo=UTC) > now:
        raise unauthorized(_ACCOUNT_LOCKED_MESSAGE, code="account_locked")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        locked_now = user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS
        if locked_now:
            user.locked_until = now + LOCKOUT_DURATION
        db.commit()
        if locked_now:
            raise unauthorized(_ACCOUNT_LOCKED_MESSAGE, code="account_locked")
        raise unauthorized(_INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return user


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    """Returns (access_token, plain_refresh_token). Persists the refresh token hash."""
    access_token = create_access_token(user.id)
    plain_refresh, token_hash, expires_at = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    db.commit()
    return access_token, plain_refresh


def rotate_refresh_token(db: Session, plain_token: str) -> tuple[User, str, str]:
    """Validates + revokes the old refresh token, issues a new pair.

    Returns (user, access_token, plain_refresh_token).
    """
    token_hash = hash_refresh_token(plain_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    stored = db.scalars(stmt).first()

    now = datetime.now(UTC)
    if (
        stored is None
        or stored.revoked_at is not None
        or stored.expires_at.replace(tzinfo=UTC) < now
    ):
        raise unauthorized("Invalid or expired refresh token", code="invalid_refresh_token")

    user = get_user_by_id(db, stored.user_id)
    if user is None or not user.is_active:
        raise unauthorized("Invalid or expired refresh token", code="invalid_refresh_token")

    stored.revoked_at = now
    access_token, plain_refresh = issue_tokens(db, user)
    return user, access_token, plain_refresh


def revoke_refresh_token(db: Session, plain_token: str) -> None:
    token_hash = hash_refresh_token(plain_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    stored = db.scalars(stmt).first()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise bad_request("Current password is incorrect", code="invalid_current_password")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    write_audit(
        db,
        actor_user_id=user.id,
        action="change_password",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()


def list_users(db: Session) -> list[User]:
    return list(db.scalars(_user_with_roles_query().order_by(User.staff_no)))


def create_user(db: Session, actor: User, staff_no: str, password: str) -> User:
    if get_user_by_staff_no(db, staff_no) is not None:
        raise conflict("A user with this staff number already exists", code="staff_no_taken")

    user = User(
        staff_no=staff_no,
        password_hash=hash_password(password),
        must_change_password=True,
        is_active=True,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_user",
        entity_type="user",
        entity_id=user.id,
        after={"staff_no": staff_no},
    )
    db.commit()
    return get_user_by_id(db, user.id)  # type: ignore[return-value]


def patch_user(db: Session, actor: User, user_id: int, is_active: bool | None) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise not_found("User not found")

    before = {"is_active": user.is_active}
    if is_active is not None:
        user.is_active = is_active
    write_audit(
        db,
        actor_user_id=actor.id,
        action="patch_user",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after={"is_active": user.is_active},
    )
    db.commit()
    return user


def assign_roles(db: Session, actor: User, user_id: int, role_codes: list[str]) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise not_found("User not found")

    roles = list(db.scalars(select(Role).where(Role.code.in_(role_codes))))
    found_codes = {role.code for role in roles}
    missing = set(role_codes) - found_codes
    if missing:
        raise bad_request(f"Unknown role codes: {', '.join(sorted(missing))}", code="unknown_role")

    before = sorted(user.role_codes)
    for user_role in list(user.user_roles):
        db.delete(user_role)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id, granted_by_user_id=actor.id))

    write_audit(
        db,
        actor_user_id=actor.id,
        action="assign_roles",
        entity_type="user",
        entity_id=user.id,
        before={"roles": before},
        after={"roles": sorted(role_codes)},
    )
    db.commit()
    return get_user_by_id(db, user.id)  # type: ignore[return-value]


def reset_password(db: Session, actor: User, user_id: int, new_password: str) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise not_found("User not found")

    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    write_audit(
        db,
        actor_user_id=actor.id,
        action="reset_password",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    return user


def list_roles(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.code)))
