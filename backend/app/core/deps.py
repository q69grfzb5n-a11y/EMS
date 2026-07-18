from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.common.enums import RoleCode
from app.common.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.auth.models import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise unauthorized("Invalid or expired token") from exc

    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized("Invalid or expired token")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_roles(*allowed: RoleCode) -> Callable[[User], User]:
    allowed_codes = {code.value for code in allowed}

    def dependency(user: CurrentUser) -> User:
        if not allowed_codes.intersection(user.role_codes):
            raise forbidden()
        return user

    return dependency
