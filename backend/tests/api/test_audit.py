from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.audit import write_audit
from app.common.models import AuditLog
from app.core.security import hash_password
from app.modules.auth.models import Role, User, UserRole

PASSWORD = "InitialPass1"


def make_user(db_session: Session, staff_no: str, roles: list[str]) -> User:
    user = User(
        staff_no=staff_no,
        password_hash=hash_password(PASSWORD),
        must_change_password=False,
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


def auth_headers(client: TestClient, staff_no: str) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login", json={"staff_no": staff_no, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_audit_log_forbidden_for_non_admin_non_hr(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "AUD1", roles=["pmo"])

    resp = client.get("/api/v1/audit-log", headers=auth_headers(client, "AUD1"))

    assert resp.status_code == 403


def test_audit_log_visible_to_hr_and_filters_by_entity_type(
    client: TestClient, db_session: Session
) -> None:
    hr = make_user(db_session, "AUD2", roles=["hr"])
    write_audit(
        db_session,
        actor_user_id=hr.id,
        action="create_department",
        entity_type="department",
        entity_id=1,
    )
    write_audit(
        db_session,
        actor_user_id=hr.id,
        action="create_position",
        entity_type="position",
        entity_id=1,
    )
    db_session.commit()

    resp = client.get(
        "/api/v1/audit-log",
        headers=auth_headers(client, "AUD2"),
        params={"entity_type": "department"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert all(item["entity_type"] == "department" for item in body["items"])
    assert body["items"][0]["actor_staff_no"] == "AUD2"


def test_audit_log_filters_by_actor_and_date_range(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, "AUD3", roles=["admin"])
    other = make_user(db_session, "AUD4", roles=["hr"])
    write_audit(
        db_session, actor_user_id=admin.id, action="x", entity_type="test_entity", entity_id=1
    )
    write_audit(
        db_session, actor_user_id=other.id, action="x", entity_type="test_entity", entity_id=2
    )
    db_session.commit()

    resp = client.get(
        "/api/v1/audit-log",
        headers=auth_headers(client, "AUD3"),
        params={"entity_type": "test_entity", "actor_user_id": admin.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["actor_user_id"] == admin.id

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp2 = client.get(
        "/api/v1/audit-log",
        headers=auth_headers(client, "AUD3"),
        params={"entity_type": "test_entity", "date_from": future},
    )
    assert resp2.json()["total"] == 0


def test_audit_log_pagination(client: TestClient, db_session: Session) -> None:
    admin = make_user(db_session, "AUD5", roles=["admin"])
    for i in range(5):
        write_audit(
            db_session,
            actor_user_id=admin.id,
            action="x",
            entity_type="pagination_test",
            entity_id=i,
        )
    db_session.commit()

    resp = client.get(
        "/api/v1/audit-log",
        headers=auth_headers(client, "AUD5"),
        params={"entity_type": "pagination_test", "limit": 2, "offset": 0},
    )
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


def test_audit_log_no_actor_shows_null_staff_no(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "AUD6", roles=["admin"])
    system_log = AuditLog(
        actor_user_id=None, action="system_event", entity_type="unattributed_test", entity_id="1"
    )
    db_session.add(system_log)
    db_session.commit()

    resp = client.get(
        "/api/v1/audit-log",
        headers=auth_headers(client, "AUD6"),
        params={"entity_type": "unattributed_test"},
    )
    body = resp.json()
    assert body["items"][0]["actor_user_id"] is None
    assert body["items"][0]["actor_staff_no"] is None
