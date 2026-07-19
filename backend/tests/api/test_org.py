from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.models import Role, User, UserRole
from app.modules.org import service
from app.modules.org.models import Position, PositionRate

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


def login(client: TestClient, staff_no: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"staff_no": staff_no, "password": password})


def auth_headers(client: TestClient, staff_no: str) -> dict[str, str]:
    token = login(client, staff_no).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_department_forbidden_for_non_hr(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "5001", roles=["admin"])
    headers = auth_headers(client, "5001")

    resp = client.post(
        "/api/v1/departments", headers=headers, json={"code": "X1", "name_en": "X", "name_ar": "س"}
    )

    assert resp.status_code == 403


def test_create_department_hr_ok_then_duplicate_code_conflict(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "5002", roles=["hr"])
    headers = auth_headers(client, "5002")

    first = client.post(
        "/api/v1/departments", headers=headers, json={"code": "X2", "name_en": "X", "name_ar": "س"}
    )
    assert first.status_code == 201

    dup = client.post(
        "/api/v1/departments", headers=headers, json={"code": "X2", "name_en": "Y", "name_ar": "ص"}
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "department_code_taken"


def test_list_departments_open_to_any_authenticated_role(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "5003", roles=["employee"])
    headers = auth_headers(client, "5003")

    resp = client.get("/api/v1/departments", headers=headers)

    assert resp.status_code == 200


def test_position_rate_overlap_is_rejected_with_409(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "5004", roles=["hr"])
    headers = auth_headers(client, "5004")

    pos_resp = client.post(
        "/api/v1/positions",
        headers=headers,
        json={"code": "posx", "title_en": "PosX", "title_ar": "وظيفة"},
    )
    assert pos_resp.status_code == 201
    position_id = pos_resp.json()["id"]

    first = client.post(
        f"/api/v1/positions/{position_id}/rates",
        headers=headers,
        json={"effective_from": "2024-01-01", "flat_ref_amount": "1000"},
    )
    assert first.status_code == 201

    overlapping = client.post(
        f"/api/v1/positions/{position_id}/rates",
        headers=headers,
        json={"effective_from": "2024-06-01", "flat_ref_amount": "1200"},
    )
    assert overlapping.status_code == 409
    assert overlapping.json()["error"]["code"] == "rate_overlap"

    adjacent_non_overlapping = client.post(
        f"/api/v1/positions/{position_id}/rates",
        headers=headers,
        json={
            "effective_from": "2020-01-01",
            "effective_to": "2024-01-01",
            "flat_ref_amount": "900",
        },
    )
    assert adjacent_non_overlapping.status_code == 201


def test_position_rate_requires_at_least_one_rate_value(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "5005", roles=["hr"])
    headers = auth_headers(client, "5005")
    pos_resp = client.post(
        "/api/v1/positions",
        headers=headers,
        json={"code": "posy", "title_en": "PosY", "title_ar": "وظيفة"},
    )
    position_id = pos_resp.json()["id"]

    resp = client.post(
        f"/api/v1/positions/{position_id}/rates",
        headers=headers,
        json={"effective_from": "2024-01-01"},
    )

    assert resp.status_code == 422


def test_rate_as_of_boundaries(db_session: Session) -> None:
    position = Position(code="posz", title_en="PosZ", title_ar="وظيفة")
    db_session.add(position)
    db_session.flush()
    db_session.add(
        PositionRate(
            position_id=position.id,
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 7, 1),
            flat_ref_amount=1000,
        )
    )
    db_session.commit()

    assert service.rate_as_of(db_session, position.id, date(2023, 12, 31)) is None
    assert service.rate_as_of(db_session, position.id, date(2024, 1, 1)) is not None
    assert service.rate_as_of(db_session, position.id, date(2024, 6, 30)) is not None
    # effective_to is exclusive — the window ends *before* this date.
    assert service.rate_as_of(db_session, position.id, date(2024, 7, 1)) is None


def test_rate_as_of_open_ended_window_covers_any_future_date(db_session: Session) -> None:
    position = Position(code="posw", title_en="PosW", title_ar="وظيفة")
    db_session.add(position)
    db_session.flush()
    db_session.add(
        PositionRate(position_id=position.id, effective_from=date(2024, 1, 1), flat_ref_amount=1000)
    )
    db_session.commit()

    assert service.rate_as_of(db_session, position.id, date(2099, 1, 1)) is not None
