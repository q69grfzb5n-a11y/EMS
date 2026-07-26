from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.common.enums import RoleCode
from app.common.errors import too_many_requests, unauthorized
from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.rate_limit import check_rate_limit, get_client_ip
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    AssignRolesRequest,
    ChangePasswordRequest,
    LinkEmployeeRequest,
    LoginRequest,
    MeResponse,
    ResetPasswordRequest,
    RoleOut,
    TokenResponse,
    UserCreateRequest,
    UserOut,
    UserPatchRequest,
)
from app.modules.employees.models import Employee

settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
# Scoped to /auth (not just /auth/refresh) so /auth/logout can read and revoke it too —
# a cookie scoped to one exact path is never sent by the browser to a sibling path.
REFRESH_COOKIE_PATH = "/api/v1/auth"

AdminOrHR = Annotated[User, Depends(require_roles(RoleCode.ADMIN, RoleCode.HR))]
HROnly = Annotated[User, Depends(require_roles(RoleCode.HR))]

# Defense-in-depth alongside the per-account lockout in auth.service: this
# limits login attempts per SOURCE IP, so an attacker enumerating many
# different staff numbers from one machine gets slowed down even though each
# individual account's own 5-attempt lockout hasn't triggered yet.
LOGIN_RATE_LIMIT_MAX = 20
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 300.0

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])
roles_router = APIRouter(prefix="/roles", tags=["roles"])


def _set_refresh_cookie(response: Response, plain_refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=plain_refresh_token,
        httponly=True,
        samesite="strict",
        secure=settings.app_env == "prod",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )


def _user_to_out(user: User, employee: Employee | None = None) -> UserOut:
    return UserOut(
        id=user.id,
        staff_no=user.staff_no,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        roles=sorted(user.role_codes),
        employee_id=user.employee_id,
        employee_staff_no=employee.staff_no if employee else None,
        employee_name_en=employee.full_name_en if employee else None,
        employee_name_ar=employee.full_name_ar if employee else None,
    )


def _users_to_out(db: DbSession, users: list[User]) -> list[UserOut]:
    """Batch-fetches the linked Employee rows in one query instead of one
    lookup per user, since the users list endpoint returns every account."""
    employee_ids = {u.employee_id for u in users if u.employee_id is not None}
    employees_by_id = (
        {e.id: e for e in db.scalars(select(Employee).where(Employee.id.in_(employee_ids)))}
        if employee_ids
        else {}
    )
    return [
        _user_to_out(u, employees_by_id.get(u.employee_id) if u.employee_id else None)
        for u in users
    ]


def _user_to_out_with_employee(db: DbSession, user: User) -> UserOut:
    employee = db.get(Employee, user.employee_id) if user.employee_id is not None else None
    return _user_to_out(user, employee)


@auth_router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession
) -> TokenResponse:
    client_ip = get_client_ip(request)
    if not check_rate_limit(
        f"login:{client_ip}",
        max_requests=LOGIN_RATE_LIMIT_MAX,
        window_seconds=LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    ):
        raise too_many_requests(
            "Too many login attempts from this address. Try again later.",
            code="login_rate_limited",
        )

    user = service.authenticate(db, payload.staff_no, payload.password)
    access_token, plain_refresh = service.issue_tokens(db, user)
    _set_refresh_cookie(response, plain_refresh)
    return TokenResponse(access_token=access_token, must_change_password=user.must_change_password)


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: DbSession) -> TokenResponse:
    plain_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if plain_token is None:
        raise unauthorized("Missing refresh token", code="missing_refresh_token")

    user, access_token, new_plain_refresh = service.rotate_refresh_token(db, plain_token)
    _set_refresh_cookie(response, new_plain_refresh)
    return TokenResponse(access_token=access_token, must_change_password=user.must_change_password)


@auth_router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DbSession) -> None:
    plain_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if plain_token is not None:
        service.revoke_refresh_token(db, plain_token)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@auth_router.get("/me", response_model=MeResponse)
def me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=user.id,
        staff_no=user.staff_no,
        roles=sorted(user.role_codes),
        must_change_password=user.must_change_password,
    )


@auth_router.post("/change-password", status_code=204)
def change_password_endpoint(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> None:
    service.change_password(db, user, payload.current_password, payload.new_password)


@users_router.get("", response_model=list[UserOut])
def list_users_endpoint(_actor: AdminOrHR, db: DbSession) -> list[UserOut]:
    return _users_to_out(db, service.list_users(db))


@users_router.post("", response_model=UserOut, status_code=201)
def create_user_endpoint(payload: UserCreateRequest, actor: AdminOrHR, db: DbSession) -> UserOut:
    user = service.create_user(db, actor, payload.staff_no, payload.password)
    # Resolve the employee too: creation now auto-links by staff number, so
    # returning the bare user would hide the link the caller just got.
    return _user_to_out_with_employee(db, user)


@users_router.patch("/{user_id}", response_model=UserOut)
def patch_user_endpoint(
    user_id: int, payload: UserPatchRequest, actor: AdminOrHR, db: DbSession
) -> UserOut:
    user = service.patch_user(db, actor, user_id, payload.is_active)
    return _user_to_out_with_employee(db, user)


@users_router.put("/{user_id}/roles", response_model=UserOut)
def assign_roles_endpoint(
    user_id: int, payload: AssignRolesRequest, actor: HROnly, db: DbSession
) -> UserOut:
    user = service.assign_roles(db, actor, user_id, payload.role_codes)
    return _user_to_out_with_employee(db, user)


@users_router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password_endpoint(
    user_id: int, payload: ResetPasswordRequest, actor: HROnly, db: DbSession
) -> UserOut:
    user = service.reset_password(db, actor, user_id, payload.new_password)
    return _user_to_out_with_employee(db, user)


@users_router.put("/{user_id}/employee", response_model=UserOut)
def link_employee_endpoint(
    user_id: int, payload: LinkEmployeeRequest, actor: HROnly, db: DbSession
) -> UserOut:
    user = service.link_employee(db, actor, user_id, payload.employee_id)
    return _user_to_out_with_employee(db, user)


@roles_router.get("", response_model=list[RoleOut])
def list_roles_endpoint(_user: CurrentUser, db: DbSession) -> list[RoleOut]:
    return [
        RoleOut(id=r.id, code=r.code, name_en=r.name_en, name_ar=r.name_ar)
        for r in service.list_roles(db)
    ]


router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(roles_router)
