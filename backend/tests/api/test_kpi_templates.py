from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.models import Role, User, UserRole
from app.modules.kpi_templates import service
from app.modules.kpi_templates.models import (
    KpiCriterion,
    KpiTemplate,
    KpiTemplateAssignment,
    KpiTemplateVersion,
)
from app.modules.org.models import Position

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


def make_template_with_criteria(
    db_session: Session, code: str, marks: list[int], *, activate: bool = False
) -> tuple[KpiTemplate, KpiTemplateVersion]:
    template = KpiTemplate(code=code, name_en=code, name_ar=code)
    db_session.add(template)
    db_session.flush()
    version = KpiTemplateVersion(template_id=template.id, version_no=1)
    db_session.add(version)
    db_session.flush()
    for i, m in enumerate(marks):
        db_session.add(
            KpiCriterion(
                template_version_id=version.id, name_en=f"C{i}", name_ar=f"C{i}", max_marks=m
            )
        )
    db_session.flush()
    if activate:
        version.status = "active"
    db_session.commit()
    db_session.refresh(version)
    return template, version


def test_create_template_forbidden_for_hr(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "7001", roles=["hr"])
    headers = auth_headers(client, "7001")

    resp = client.post(
        "/api/v1/kpi-templates",
        headers=headers,
        json={"code": "X1", "name_en": "X", "name_ar": "س"},
    )

    assert resp.status_code == 403


def test_create_template_allowed_for_pmo_creates_draft_v1(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "7002", roles=["pmo"])
    headers = auth_headers(client, "7002")

    resp = client.post(
        "/api/v1/kpi-templates",
        headers=headers,
        json={"code": "X2", "name_en": "X", "name_ar": "س"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["active_version"] is None

    template_id = body["id"]
    versions = client.get(f"/api/v1/kpi-templates/{template_id}/versions", headers=headers).json()
    assert len(versions) == 1
    assert versions[0]["status"] == "draft"
    assert versions[0]["version_no"] == 1


def test_list_templates_open_to_any_authenticated_role(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "7003", roles=["employee"])
    headers = auth_headers(client, "7003")

    resp = client.get("/api/v1/kpi-templates", headers=headers)

    assert resp.status_code == 200


def test_activate_rejects_sum_not_100(client: TestClient, db_session: Session) -> None:
    _template, version = make_template_with_criteria(db_session, "SUMBAD", [30, 20, 10])
    make_user(db_session, "7004", roles=["pmo"])
    headers = auth_headers(client, "7004")

    resp = client.post(f"/api/v1/kpi-templates/versions/{version.id}/activate", headers=headers)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "criteria_sum_invalid"


def test_activate_accepts_sum_100_and_archives_previous_active(
    client: TestClient, db_session: Session
) -> None:
    template, v1 = make_template_with_criteria(
        db_session, "SWAP", [30, 20, 10, 10, 10, 10, 5, 5], activate=True
    )
    # a second draft version, cloned-equivalent criteria
    v2 = KpiTemplateVersion(template_id=template.id, version_no=2)
    db_session.add(v2)
    db_session.flush()
    for i, m in enumerate([30, 20, 10, 10, 10, 10, 5, 5]):
        db_session.add(
            KpiCriterion(template_version_id=v2.id, name_en=f"C{i}", name_ar=f"C{i}", max_marks=m)
        )
    db_session.commit()

    make_user(db_session, "7005", roles=["pmo"])
    headers = auth_headers(client, "7005")

    resp = client.post(f"/api/v1/kpi-templates/versions/{v2.id}/activate", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    db_session.refresh(v1)
    assert v1.status == "archived"


def test_criteria_editable_only_while_draft(client: TestClient, db_session: Session) -> None:
    _template, version = make_template_with_criteria(db_session, "FROZEN", [100], activate=True)
    make_user(db_session, "7006", roles=["pmo"])
    headers = auth_headers(client, "7006")

    resp = client.post(
        f"/api/v1/kpi-templates/versions/{version.id}/criteria",
        headers=headers,
        json={"name_en": "New", "name_ar": "جديد", "max_marks": 10},
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "version_not_draft"


def test_clone_version_copies_criteria_and_leaves_source_untouched(
    client: TestClient, db_session: Session
) -> None:
    template, v1 = make_template_with_criteria(db_session, "CLONEME", [60, 40], activate=True)
    make_user(db_session, "7007", roles=["pmo"])
    headers = auth_headers(client, "7007")

    resp = client.post(f"/api/v1/kpi-templates/{template.id}/versions", headers=headers, json={})

    assert resp.status_code == 201
    v2 = resp.json()
    assert v2["version_no"] == 2
    assert v2["status"] == "draft"
    assert sorted(c["max_marks"] for c in v2["criteria"]) == [40, 60]

    db_session.refresh(v1)
    assert v1.status == "active"
    assert len(v1.criteria) == 2


def test_kpi_template_assignment_requires_pmo_or_hr(
    client: TestClient, db_session: Session
) -> None:
    position = Position(code="posk", title_en="PosK", title_ar="وظيفة")
    db_session.add(position)
    db_session.flush()
    template, _v1 = make_template_with_criteria(db_session, "ASSIGN1", [100], activate=True)
    db_session.commit()
    make_user(db_session, "7008", roles=["reviewer"])
    headers = auth_headers(client, "7008")

    resp = client.post(
        f"/api/v1/positions/{position.id}/kpi-template-assignments",
        headers=headers,
        json={"template_id": template.id, "effective_from": "2024-01-01"},
    )

    assert resp.status_code == 403


def test_kpi_template_assignment_overlap_rejected(client: TestClient, db_session: Session) -> None:
    position = Position(code="posl", title_en="PosL", title_ar="وظيفة")
    db_session.add(position)
    db_session.flush()
    template, _v1 = make_template_with_criteria(db_session, "ASSIGN2", [100], activate=True)
    db_session.commit()
    make_user(db_session, "7009", roles=["pmo"])
    headers = auth_headers(client, "7009")

    first = client.post(
        f"/api/v1/positions/{position.id}/kpi-template-assignments",
        headers=headers,
        json={"template_id": template.id, "effective_from": "2024-01-01"},
    )
    assert first.status_code == 201

    overlapping = client.post(
        f"/api/v1/positions/{position.id}/kpi-template-assignments",
        headers=headers,
        json={"template_id": template.id, "effective_from": "2024-06-01"},
    )
    assert overlapping.status_code == 409
    assert overlapping.json()["error"]["code"] == "assignment_overlap"


def test_resolve_template_for_position_as_of_boundaries(db_session: Session) -> None:
    position = Position(code="posm", title_en="PosM", title_ar="وظيفة")
    db_session.add(position)
    db_session.flush()
    template, _v1 = make_template_with_criteria(db_session, "RESOLVE1", [100], activate=True)
    db_session.commit()

    db_session.add(
        KpiTemplateAssignment(
            position_id=position.id,
            template_id=template.id,
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 7, 1),
        )
    )
    db_session.commit()

    assert (
        service.resolve_template_for_position(db_session, position.id, date(2023, 12, 31)) is None
    )
    resolved = service.resolve_template_for_position(db_session, position.id, date(2024, 1, 1))
    assert resolved is not None and resolved.id == template.id
    assert service.resolve_template_for_position(db_session, position.id, date(2024, 7, 1)) is None
