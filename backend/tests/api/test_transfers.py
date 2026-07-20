from dataclasses import dataclass
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.models import Role, User, UserRole
from app.modules.employees.models import Employee
from app.modules.org.models import Department, Position
from app.modules.transfers import service
from app.modules.transfers.models import TransferRequest

PASSWORD = "InitialPass1"


def make_user(
    db_session: Session, staff_no: str, roles: list[str], employee_id: int | None = None
) -> User:
    user = User(
        staff_no=staff_no,
        password_hash=hash_password(PASSWORD),
        must_change_password=False,
        is_active=True,
        employee_id=employee_id,
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


@dataclass
class Fixture:
    dept_a: Department
    dept_b: Department
    employee: Employee
    hr: User
    dept_manager_a: User
    dept_manager_b: User
    pmo: User
    fm: User


def build_fixture(db_session: Session, *, suffix: str) -> Fixture:
    dept_a = Department(code=f"TA{suffix}", name_en=f"Dept A{suffix}", name_ar="قسم أ")
    dept_b = Department(code=f"TB{suffix}", name_en=f"Dept B{suffix}", name_ar="قسم ب")
    position = Position(code=f"tpos{suffix}", title_en=f"Pos {suffix}", title_ar="وظيفة")
    db_session.add_all([dept_a, dept_b, position])
    db_session.flush()

    employee = Employee(
        staff_no=f"TEMP{suffix}",
        full_name_ar="اسم الموظف",
        department_id=dept_a.id,
        position_id=position.id,
    )
    db_session.add(employee)
    db_session.flush()

    mgr_a_employee = Employee(
        staff_no=f"TMGRA{suffix}", full_name_ar="مدير أ", department_id=dept_a.id, position_id=position.id
    )
    mgr_b_employee = Employee(
        staff_no=f"TMGRB{suffix}", full_name_ar="مدير ب", department_id=dept_b.id, position_id=position.id
    )
    db_session.add_all([mgr_a_employee, mgr_b_employee])
    db_session.flush()

    hr = make_user(db_session, f"THR{suffix}", roles=["hr"])
    dept_manager_a = make_user(
        db_session, f"TMA{suffix}", roles=["dept_manager"], employee_id=mgr_a_employee.id
    )
    dept_manager_b = make_user(
        db_session, f"TMB{suffix}", roles=["dept_manager"], employee_id=mgr_b_employee.id
    )
    pmo = make_user(db_session, f"TPMO{suffix}", roles=["pmo"])
    fm = make_user(db_session, f"TFM{suffix}", roles=["factory_manager"])

    db_session.commit()
    return Fixture(
        dept_a=dept_a,
        dept_b=dept_b,
        employee=employee,
        hr=hr,
        dept_manager_a=dept_manager_a,
        dept_manager_b=dept_manager_b,
        pmo=pmo,
        fm=fm,
    )


def create_transfer(
    client: TestClient,
    fx: Fixture,
    *,
    requester: User,
    effective_date: date,
    to_department_id: int | None = None,
):
    return client.post(
        "/api/v1/transfers",
        headers=auth_headers(client, requester.staff_no),
        json={
            "employee_id": fx.employee.id,
            "to_department_id": to_department_id if to_department_id is not None else fx.dept_b.id,
            "effective_date": effective_date.isoformat(),
            "reason": "team rebalance",
        },
    )


# ---- creation --------------------------------------------------------------


def test_create_transfer_snapshots_from_department(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="1")

    resp = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1))

    assert resp.status_code == 201
    body = resp.json()
    assert body["from_department"]["id"] == fx.dept_a.id
    assert body["to_department"]["id"] == fx.dept_b.id
    assert body["status"] == "draft"
    assert body["requested_by_user_id"] == fx.hr.id


def test_create_transfer_rejects_same_department(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="2")

    resp = create_transfer(
        client, fx, requester=fx.hr, effective_date=date(2026, 8, 1), to_department_id=fx.dept_a.id
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "same_department"


def test_create_transfer_rejects_duplicate_pending(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="3")
    first = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1))
    assert first.status_code == 201

    second = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 9, 1))

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "employee_has_pending_transfer"


def test_dept_manager_can_request_for_own_department_only(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="4")

    own_dept = create_transfer(client, fx, requester=fx.dept_manager_a, effective_date=date(2026, 8, 1))
    assert own_dept.status_code == 201

    fx2 = build_fixture(db_session, suffix="5")
    other_dept = create_transfer(
        client, fx2, requester=fx.dept_manager_b, effective_date=date(2026, 8, 1)
    )
    assert other_dept.status_code == 403


def test_create_transfer_requires_hr_dept_manager_or_admin(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="6")

    resp = client.post(
        "/api/v1/transfers",
        headers=auth_headers(client, fx.pmo.staff_no),
        json={
            "employee_id": fx.employee.id,
            "to_department_id": fx.dept_b.id,
            "effective_date": "2026-08-01",
        },
    )

    assert resp.status_code == 403


# ---- transition matrix + effective-date apply ------------------------------


def test_full_workflow_applies_immediately_when_effective_date_has_arrived(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="7")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)

    created = create_transfer(client, fx, requester=fx.hr, effective_date=date.today()).json()
    transfer_id = created["id"]

    submitted = client.post(f"/api/v1/transfers/{transfer_id}/submit", headers=hr_headers, json={})
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    reviewed = client.post(f"/api/v1/transfers/{transfer_id}/review", headers=pmo_headers, json={})
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "pmo_reviewed"

    approved = client.post(f"/api/v1/transfers/{transfer_id}/approve", headers=fm_headers, json={})
    assert approved.status_code == 200
    # effective_date == today, so the lazy apply-if-due pass fires right after approval
    assert approved.json()["status"] == "applied"

    db_session.expire_all()
    employee = db_session.get(Employee, fx.employee.id)
    assert employee is not None
    assert employee.department_id == fx.dept_b.id


def test_future_effective_date_not_applied_until_due(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="8")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)

    future_date = date.today() + timedelta(days=60)
    created = create_transfer(client, fx, requester=fx.hr, effective_date=future_date).json()
    transfer_id = created["id"]

    client.post(f"/api/v1/transfers/{transfer_id}/submit", headers=hr_headers, json={})
    client.post(f"/api/v1/transfers/{transfer_id}/review", headers=pmo_headers, json={})
    approved = client.post(f"/api/v1/transfers/{transfer_id}/approve", headers=fm_headers, json={})

    assert approved.status_code == 200
    assert approved.json()["status"] == "fm_approved"  # not applied yet

    db_session.expire_all()
    employee = db_session.get(Employee, fx.employee.id)
    assert employee is not None
    assert employee.department_id == fx.dept_a.id  # still the old department

    # Simulate the effective_date arriving (no scheduler in this project — the
    # apply pass runs lazily the next time anyone reads the transfers module).
    transfer = db_session.get(TransferRequest, transfer_id)
    assert transfer is not None
    transfer.effective_date = date.today() - timedelta(days=1)
    db_session.commit()

    listed = client.get("/api/v1/transfers", headers=hr_headers)
    assert listed.status_code == 200
    applied_entry = next(t for t in listed.json() if t["id"] == transfer_id)
    assert applied_entry["status"] == "applied"

    db_session.expire_all()
    employee_after = db_session.get(Employee, fx.employee.id)
    assert employee_after is not None
    assert employee_after.department_id == fx.dept_b.id


def test_return_loop_then_resubmit(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="9")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)

    created = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1)).json()
    transfer_id = created["id"]
    client.post(f"/api/v1/transfers/{transfer_id}/submit", headers=hr_headers, json={})

    returned = client.post(
        f"/api/v1/transfers/{transfer_id}/return",
        headers=pmo_headers,
        json={"comment": "need more detail"},
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "returned"

    resubmit = client.post(f"/api/v1/transfers/{transfer_id}/submit", headers=hr_headers, json={})
    assert resubmit.status_code == 200
    assert resubmit.json()["status"] == "submitted"

    history = client.get(
        f"/api/v1/approvals/transfer/{transfer_id}/history", headers=hr_headers
    ).json()
    assert [h["action"] for h in history] == ["submit", "return", "submit"]
    assert history[1]["comment"] == "need more detail"


def test_pmo_action_forbidden_for_dept_manager(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="10")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    created = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1)).json()
    client.post(f"/api/v1/transfers/{created['id']}/submit", headers=hr_headers, json={})

    resp = client.post(
        f"/api/v1/transfers/{created['id']}/review",
        headers=auth_headers(client, fx.dept_manager_a.staff_no),
        json={},
    )
    assert resp.status_code == 403


def test_approve_before_review_is_invalid_transition(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="11")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    created = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1)).json()
    client.post(f"/api/v1/transfers/{created['id']}/submit", headers=hr_headers, json={})

    resp = client.post(
        f"/api/v1/transfers/{created['id']}/approve",
        headers=auth_headers(client, fx.fm.staff_no),
        json={},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_transition"


# ---- view scoping -----------------------------------------------------------


def test_unrelated_dept_manager_cannot_view_transfer(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="12")
    # a manager whose department is neither the from- nor to-department of this
    # transfer (dept_manager_b is the *destination* manager, which is legitimately
    # allowed — see test_destination_dept_manager_can_view_transfer below).
    unrelated_fx = build_fixture(db_session, suffix="12b")
    created = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1)).json()

    resp = client.get(
        f"/api/v1/transfers/{created['id']}",
        headers=auth_headers(client, unrelated_fx.dept_manager_a.staff_no),
    )
    assert resp.status_code == 403

    listed = client.get(
        "/api/v1/transfers", headers=auth_headers(client, unrelated_fx.dept_manager_a.staff_no)
    )
    assert not any(t["id"] == created["id"] for t in listed.json())


def test_destination_dept_manager_can_view_transfer(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="13")
    created = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1)).json()

    resp = client.get(
        f"/api/v1/transfers/{created['id']}",
        headers=auth_headers(client, fx.dept_manager_b.staff_no),
    )
    assert resp.status_code == 200


# ---- unified inbox -----------------------------------------------------------


def test_pmo_pending_inbox_includes_submitted_transfer(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="14")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)

    created = create_transfer(client, fx, requester=fx.hr, effective_date=date(2026, 8, 1)).json()

    before = client.get("/api/v1/approvals/pending", headers=pmo_headers).json()
    assert not any(i["entity_type"] == "transfer" and i["id"] == created["id"] for i in before)

    client.post(f"/api/v1/transfers/{created['id']}/submit", headers=hr_headers, json={})

    after = client.get("/api/v1/approvals/pending", headers=pmo_headers).json()
    match = next(i for i in after if i["entity_type"] == "transfer" and i["id"] == created["id"])
    assert match["status"] == "submitted"
    assert match["employee"]["id"] == fx.employee.id


def test_service_get_history_404_for_missing_transfer(db_session: Session) -> None:
    from app.common.errors import AppError

    try:
        service.get_history(db_session, 999999)
        raise AssertionError("expected not_found")
    except AppError as exc:
        assert exc.status_code == 404
