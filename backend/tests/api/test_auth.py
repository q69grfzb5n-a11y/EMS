from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth import router as auth_router
from app.modules.auth import service as auth_service
from app.modules.auth.models import Role, User, UserRole

PASSWORD = "InitialPass1"


def make_user(
    db_session: Session, staff_no: str, roles: list[str], must_change_password: bool = False
) -> User:
    user = User(
        staff_no=staff_no,
        password_hash=hash_password(PASSWORD),
        must_change_password=must_change_password,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    for code in roles:
        role = db_session.scalars(select(Role).where(Role.code == code)).first()
        if role is None:
            role = Role(code=code, name_en=code, name_ar=code)
            db_session.add(role)
            db_session.flush()
        db_session.add(UserRole(user_id=user.id, role_id=role.id))

    db_session.commit()
    db_session.refresh(user)
    return user


def ensure_roles(db_session: Session, codes: list[str]) -> None:
    for code in codes:
        if db_session.scalars(select(Role).where(Role.code == code)).first() is None:
            db_session.add(Role(code=code, name_en=code, name_ar=code))
    db_session.commit()


def login(client: TestClient, staff_no: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"staff_no": staff_no, "password": password})


def test_login_success_returns_token_and_sets_cookie(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "1001", roles=["employee"])

    resp = login(client, "1001")

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["must_change_password"] is False
    assert "refresh_token" in resp.cookies


def test_login_wrong_password_401(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "1002", roles=["employee"])

    resp = login(client, "1002", password="wrong-password")

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_staff_no_401(client: TestClient) -> None:
    resp = login(client, "9999")
    assert resp.status_code == 401


def test_login_rate_limited_after_too_many_attempts_from_one_source(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "1008", roles=["employee"])

    for _ in range(auth_router.LOGIN_RATE_LIMIT_MAX):
        login(client, "1008")

    limited = login(client, "1008")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "login_rate_limited"


def test_repeated_failed_logins_lock_the_account(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "1006", roles=["employee"])

    for _ in range(auth_service.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        resp = login(client, "1006", password="wrong-password")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "invalid_credentials"

    locking_attempt = login(client, "1006", password="wrong-password")
    assert locking_attempt.status_code == 401
    assert locking_attempt.json()["error"]["code"] == "account_locked"

    # Even the CORRECT password is refused while locked.
    still_locked = login(client, "1006")
    assert still_locked.status_code == 401
    assert still_locked.json()["error"]["code"] == "account_locked"


def test_successful_login_resets_the_failed_attempt_counter(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "1007", roles=["employee"])

    for _ in range(auth_service.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        login(client, "1007", password="wrong-password")

    ok = login(client, "1007")
    assert ok.status_code == 200

    user = db_session.scalars(select(User).where(User.staff_no == "1007")).first()
    assert user is not None
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_me_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "1003", roles=["employee", "reviewer"])
    token = login(client, "1003").json()["access_token"]

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["staff_no"] == "1003"
    assert sorted(body["roles"]) == ["employee", "reviewer"]


def test_change_password_flow(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "1004", roles=["employee"], must_change_password=True)
    token = login(client, "1004").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    wrong = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "BrandNewPass1"},
    )
    assert wrong.status_code == 400

    ok = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "BrandNewPass1"},
    )
    assert ok.status_code == 204

    relogin = login(client, "1004", password="BrandNewPass1")
    assert relogin.status_code == 200
    assert relogin.json()["must_change_password"] is False


def test_must_change_password_blocks_other_endpoints_server_side(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "1005", roles=["employee"], must_change_password=True)
    token = login(client, "1005").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # A direct API call (not the browser UI) with a valid token must still be
    # blocked from any endpoint other than the two needed to escape the gate.
    blocked = client.get("/api/v1/roles", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "BrandNewPass2"},
    )
    assert changed.status_code == 204

    now_allowed = client.get("/api/v1/roles", headers=headers)
    assert now_allowed.status_code == 200


def test_refresh_rotation_revokes_old_token(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "1005", roles=["employee"])
    login_resp = login(client, "1005")
    old_cookie = login_resp.cookies.get("refresh_token")

    rotate_resp = client.post("/api/v1/auth/refresh")
    assert rotate_resp.status_code == 200
    new_cookie = rotate_resp.cookies.get("refresh_token")
    assert new_cookie != old_cookie

    replay = client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_cookie})
    assert replay.status_code == 401


def test_refresh_without_cookie_401(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "1006", roles=["employee"])
    login(client, "1006")

    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204

    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 401


def test_assign_roles_forbidden_for_admin(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, "2001", roles=["admin"])
    target = make_user(db_session, "2002", roles=["employee"])
    token = login(client, "2001").json()["access_token"]

    resp = client.put(
        f"/api/v1/users/{target.id}/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"role_codes": ["reviewer"]},
    )

    assert resp.status_code == 403
    assert admin.role_codes == ["admin"]


def test_assign_roles_allowed_for_hr(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "2003", roles=["hr"])
    target = make_user(db_session, "2004", roles=["employee"])
    ensure_roles(db_session, ["reviewer", "dept_manager"])
    token = login(client, "2003").json()["access_token"]

    resp = client.put(
        f"/api/v1/users/{target.id}/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"role_codes": ["reviewer", "dept_manager"]},
    )

    assert resp.status_code == 200
    assert sorted(resp.json()["roles"]) == ["dept_manager", "reviewer"]


def test_list_users_forbidden_for_reviewer(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "2005", roles=["reviewer"])
    token = login(client, "2005").json()["access_token"]

    resp = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403


def test_create_user_conflict_on_duplicate_staff_no(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "2006", roles=["hr"])
    token = login(client, "2006").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/api/v1/users", headers=headers, json={"staff_no": "3001", "password": "SomePass1"}
    )
    assert first.status_code == 201

    dup = client.post(
        "/api/v1/users", headers=headers, json={"staff_no": "3001", "password": "SomePass1"}
    )
    assert dup.status_code == 409


def test_audit_log_written_on_role_assignment(client: TestClient, db_session: Session) -> None:
    from app.common.models import AuditLog

    hr = make_user(db_session, "2007", roles=["hr"])
    target = make_user(db_session, "2008", roles=[])
    ensure_roles(db_session, ["finance"])
    token = login(client, "2007").json()["access_token"]

    resp = client.put(
        f"/api/v1/users/{target.id}/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"role_codes": ["finance"]},
    )
    assert resp.status_code == 200

    rows = db_session.scalars(select(AuditLog).where(AuditLog.action == "assign_roles")).all()
    assert len(rows) == 1
    assert rows[0].actor_user_id == hr.id
    assert rows[0].entity_id == str(target.id)
