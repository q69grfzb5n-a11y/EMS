from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.common.enums import RoleCode
from app.common.errors import unauthorized
from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    AssignRolesRequest,
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
    ResetPasswordRequest,
    RoleOut,
    TokenResponse,
    UserCreateRequest,
    UserOut,
    UserPatchRequest,
)

settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
# Scoped to /auth (not just /auth/refresh) so /auth/logout can read and revoke it too —
# a cookie scoped to one exact path is never sent by the browser to a sibling path.
REFRESH_COOKIE_PATH = "/api/v1/auth"

AdminOrHR = Annotated[User, Depends(require_roles(RoleCode.ADMIN, RoleCode.HR))]
HROnly = Annotated[User, Depends(require_roles(RoleCode.HR))]

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


def _user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        staff_no=user.staff_no,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        roles=sorted(user.role_codes),
    )


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
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
    return [_user_to_out(u) for u in service.list_users(db)]


@users_router.post("", response_model=UserOut, status_code=201)
def create_user_endpoint(payload: UserCreateRequest, actor: AdminOrHR, db: DbSession) -> UserOut:
    user = service.create_user(db, actor, payload.staff_no, payload.password)
    return _user_to_out(user)


@users_router.patch("/{user_id}", response_model=UserOut)
def patch_user_endpoint(
    user_id: int, payload: UserPatchRequest, actor: AdminOrHR, db: DbSession
) -> UserOut:
    user = service.patch_user(db, actor, user_id, payload.is_active)
    return _user_to_out(user)


@users_router.put("/{user_id}/roles", response_model=UserOut)
def assign_roles_endpoint(
    user_id: int, payload: AssignRolesRequest, actor: HROnly, db: DbSession
) -> UserOut:
    user = service.assign_roles(db, actor, user_id, payload.role_codes)
    return _user_to_out(user)


@users_router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password_endpoint(
    user_id: int, payload: ResetPasswordRequest, actor: HROnly, db: DbSession
) -> UserOut:
    user = service.reset_password(db, actor, user_id, payload.new_password)
    return _user_to_out(user)


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
