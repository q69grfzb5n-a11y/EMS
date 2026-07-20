from io import BytesIO

import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.attendance.importer import EXPECTED_HEADERS, REQUIRED_SHEET_NAME
from app.modules.attendance.models import AttendanceImport, AttendanceZeroFlag
from app.modules.auth.models import Role, User, UserRole
from app.modules.employees.models import Employee
from app.modules.org.models import Department, Position

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


def login(client: TestClient, staff_no: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"staff_no": staff_no, "password": password})


def auth_headers(client: TestClient, staff_no: str) -> dict[str, str]:
    token = login(client, staff_no).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_org(db_session: Session) -> tuple[Department, Position]:
    dept = Department(code="ADEPT", name_en="A Dept", name_ar="أ")
    position = Position(code="aposn", title_en="APos", title_ar="وظيفة")
    db_session.add_all([dept, position])
    db_session.flush()
    return dept, position


def make_employee(
    db_session: Session,
    staff_no: str,
    dept: Department,
    position: Position,
    *,
    contract_years: int | None = None,
) -> Employee:
    employee = Employee(
        staff_no=staff_no,
        full_name_ar="اسم الموظف",
        department_id=dept.id,
        position_id=position.id,
        contract_years=contract_years,
    )
    db_session.add(employee)
    db_session.flush()
    return employee


def attendance_row(
    person_no: str,
    *,
    month: str,
    present: int,
    off_days: int,
    absent: int,
    leave: int,
    holiday: int = 0,
) -> list[object]:
    return [
        month,
        person_no,
        "DOE, JOHN",
        "Oracle Dept",
        "Site",
        "SAJCO",
        present,
        off_days,
        absent,
        leave,
        holiday,
        0,
        0,
        present,
        0,
        0,
        0,
    ]


def build_workbook(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = REQUIRED_SHEET_NAME
    ws.append(list(EXPECTED_HEADERS))
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def upload(
    client: TestClient, headers: dict[str, str], period_id: int, content: bytes, *, dry_run: bool
):
    return client.post(
        f"/api/v1/attendance/periods/{period_id}/imports",
        headers=headers,
        params={"dry_run": str(dry_run).lower()},
        files={"file": ("attendance.xlsx", content, "application/octet-stream")},
    )


def test_create_period_forbidden_for_reviewer(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "8001", roles=["reviewer"])
    headers = auth_headers(client, "8001")

    resp = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    )

    assert resp.status_code == 403


def test_create_period_allowed_for_hr_and_is_idempotent(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "8002", roles=["hr"])
    headers = auth_headers(client, "8002")

    first = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_dry_run_preview_reports_matched_and_unmatched(
    client: TestClient, db_session: Session
) -> None:
    dept, position = make_org(db_session)
    make_employee(db_session, "3001", dept, position)
    db_session.commit()
    make_user(db_session, "8003", roles=["hr"])
    headers = auth_headers(client, "8003")

    period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    ).json()
    content = build_workbook(
        [
            attendance_row("3001", month="06-2026", present=22, off_days=4, absent=2, leave=2),
            attendance_row("9999", month="06-2026", present=22, off_days=4, absent=2, leave=2),
        ]
    )

    resp = upload(client, headers, period["id"], content, dry_run=True)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_rows"] == 2
    assert body["matched_count"] == 1
    assert body["unmatched_count"] == 1
    assert body["unmatched_staff_nos"] == ["9999"]
    assert body["has_errors"] is False

    # dry run must not have written anything
    assert db_session.scalars(select(AttendanceImport)).first() is None


def test_commit_creates_records_for_matched_employee_only(
    client: TestClient, db_session: Session
) -> None:
    dept, position = make_org(db_session)
    employee = make_employee(db_session, "3002", dept, position)
    db_session.commit()
    make_user(db_session, "8004", roles=["hr"])
    headers = auth_headers(client, "8004")

    period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    ).json()
    content = build_workbook(
        [attendance_row("3002", month="06-2026", present=22, off_days=4, absent=2, leave=2)]
    )

    resp = upload(client, headers, period["id"], content, dry_run=False)

    assert resp.status_code == 201
    assert resp.json()["row_count"] == 1

    records = client.get(
        f"/api/v1/attendance/periods/{period['id']}/records", headers=headers
    ).json()
    assert len(records) == 1
    assert records[0]["employee"]["id"] == employee.id
    assert records[0]["present"] == 22


def test_commit_duplicate_file_is_409(client: TestClient, db_session: Session) -> None:
    dept, position = make_org(db_session)
    make_employee(db_session, "3003", dept, position)
    db_session.commit()
    make_user(db_session, "8005", roles=["hr"])
    headers = auth_headers(client, "8005")

    period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    ).json()
    content = build_workbook(
        [attendance_row("3003", month="06-2026", present=22, off_days=4, absent=2, leave=2)]
    )

    first = upload(client, headers, period["id"], content, dry_run=False)
    assert first.status_code == 201

    second = upload(client, headers, period["id"], content, dry_run=False)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "duplicate_import"


def test_commit_different_file_supersedes_prior_import(
    client: TestClient, db_session: Session
) -> None:
    dept, position = make_org(db_session)
    make_employee(db_session, "3004", dept, position)
    db_session.commit()
    make_user(db_session, "8006", roles=["hr"])
    headers = auth_headers(client, "8006")

    period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    ).json()

    first_content = build_workbook(
        [attendance_row("3004", month="06-2026", present=22, off_days=4, absent=2, leave=2)]
    )
    first = upload(client, headers, period["id"], first_content, dry_run=False)
    assert first.status_code == 201
    first_id = first.json()["id"]

    second_content = build_workbook(
        [attendance_row("3004", month="06-2026", present=20, off_days=4, absent=4, leave=2)]
    )
    second = upload(client, headers, period["id"], second_content, dry_run=False)
    assert second.status_code == 201

    imports = client.get(
        f"/api/v1/attendance/periods/{period['id']}/imports", headers=headers
    ).json()
    by_id = {i["id"]: i for i in imports}
    assert by_id[first_id]["status"] == "superseded"
    assert by_id[second.json()["id"]]["status"] == "active"

    records = client.get(
        f"/api/v1/attendance/periods/{period['id']}/records", headers=headers
    ).json()
    assert len(records) == 1
    assert records[0]["present"] == 20  # upserted to the latest values


def test_commit_rejected_when_period_locked(client: TestClient, db_session: Session) -> None:
    dept, position = make_org(db_session)
    make_employee(db_session, "3005", dept, position)
    db_session.commit()
    make_user(db_session, "8007", roles=["hr"])
    headers = auth_headers(client, "8007")

    period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    ).json()
    client.post(f"/api/v1/attendance/periods/{period['id']}/lock", headers=headers)

    content = build_workbook(
        [attendance_row("3005", month="06-2026", present=22, off_days=4, absent=2, leave=2)]
    )
    resp = upload(client, headers, period["id"], content, dry_run=False)

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "period_locked"


def test_commit_with_wrong_header_returns_400_and_writes_nothing(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "8008", roles=["hr"])
    headers = auth_headers(client, "8008")

    period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    ).json()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = REQUIRED_SHEET_NAME
    bad_header = list(EXPECTED_HEADERS)
    bad_header[0] = "Period"
    ws.append(bad_header)
    buf = BytesIO()
    wb.save(buf)

    resp = upload(client, headers, period["id"], buf.getvalue(), dry_run=False)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "import_has_errors"
    assert db_session.scalars(select(AttendanceImport)).first() is None


def test_records_scoped_hidden_from_unrelated_reviewer(
    client: TestClient, db_session: Session
) -> None:
    dept, position = make_org(db_session)
    make_employee(db_session, "3006", dept, position)
    db_session.commit()
    make_user(db_session, "8009", roles=["hr"])
    hr_headers = auth_headers(client, "8009")

    period = client.post(
        "/api/v1/attendance/periods", headers=hr_headers, json={"year": 2026, "month": 6}
    ).json()
    content = build_workbook(
        [attendance_row("3006", month="06-2026", present=22, off_days=4, absent=2, leave=2)]
    )
    upload(client, hr_headers, period["id"], content, dry_run=False)

    make_user(db_session, "8010", roles=["reviewer"])
    reviewer_headers = auth_headers(client, "8010")
    resp = client.get(
        f"/api/v1/attendance/periods/{period['id']}/records", headers=reviewer_headers
    )

    assert resp.status_code == 200
    assert resp.json() == []


def test_zero_flag_created_after_two_periods_breach_allowance_and_hr_can_override(
    client: TestClient, db_session: Session
) -> None:
    dept, position = make_org(db_session)
    make_employee(db_session, "3007", dept, position, contract_years=1)
    db_session.commit()
    make_user(db_session, "8011", roles=["hr"])
    headers = auth_headers(client, "8011")

    may_period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 5}
    ).json()
    june_period = client.post(
        "/api/v1/attendance/periods", headers=headers, json={"year": 2026, "month": 6}
    ).json()

    # May 2026 has 31 days: 6 present + 10 absent + 15 leave = 31
    may_content = build_workbook(
        [attendance_row("3007", month="05-2026", present=6, off_days=0, absent=10, leave=15)]
    )
    assert upload(client, headers, may_period["id"], may_content, dry_run=False).status_code == 201

    # June 2026 has 30 days: 5 present + 10 absent + 15 leave = 30
    june_content = build_workbook(
        [attendance_row("3007", month="06-2026", present=5, off_days=0, absent=10, leave=15)]
    )
    assert (
        upload(client, headers, june_period["id"], june_content, dry_run=False).status_code == 201
    )

    # total leave+absent across the two periods = 50 > 45 (1-year contract allowance)
    flags = db_session.scalars(select(AttendanceZeroFlag)).all()
    assert len(flags) == 1
    flag = flags[0]
    assert flag.total_leave_absence_days == 50
    assert flag.allowance_days == 45
    assert flag.is_overridden is False

    resp = client.post(
        f"/api/v1/attendance/zero-flags/{flag.id}/override",
        headers=headers,
        json={"reason": "Approved medical leave, not counted against allowance"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_overridden"] is True

    make_user(db_session, "8012", roles=["reviewer"])
    reviewer_headers = auth_headers(client, "8012")
    forbidden = client.post(
        f"/api/v1/attendance/zero-flags/{flag.id}/override",
        headers=reviewer_headers,
        json={"reason": "not allowed"},
    )
    assert forbidden.status_code == 403
