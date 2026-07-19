from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.models import Role, User, UserRole
from app.modules.employees import service
from app.modules.employees.models import Employee, EmployeeSalary, EvaluationAssignment
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


def make_org(db_session: Session) -> tuple[Department, Department, Position]:
    dept_a = Department(code="DA", name_en="Dept A", name_ar="أ")
    dept_b = Department(code="DB", name_en="Dept B", name_ar="ب")
    position = Position(code="posz", title_en="PosZ", title_ar="وظيفة")
    db_session.add_all([dept_a, dept_b, position])
    db_session.flush()
    return dept_a, dept_b, position


def make_employee(
    db_session: Session, staff_no: str, dept: Department, position: Position
) -> Employee:
    employee = Employee(
        staff_no=staff_no, full_name_ar="اسم الموظف", department_id=dept.id, position_id=position.id
    )
    db_session.add(employee)
    db_session.flush()
    return employee


def test_create_employee_forbidden_for_non_hr(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    db_session.commit()
    make_user(db_session, "6001", roles=["reviewer"])
    headers = auth_headers(client, "6001")

    resp = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "staff_no": "E900",
            "full_name_ar": "اسم",
            "department_id": dept_a.id,
            "position_id": position.id,
        },
    )

    assert resp.status_code == 403


def test_create_employee_duplicate_staff_no_conflict(
    client: TestClient, db_session: Session
) -> None:
    dept_a, _, position = make_org(db_session)
    db_session.commit()
    make_user(db_session, "6002", roles=["hr"])
    headers = auth_headers(client, "6002")
    payload = {
        "staff_no": "E901",
        "full_name_ar": "اسم",
        "department_id": dept_a.id,
        "position_id": position.id,
    }

    first = client.post("/api/v1/employees", headers=headers, json=payload)
    assert first.status_code == 201

    dup = client.post("/api/v1/employees", headers=headers, json=payload)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "staff_no_taken"


def test_dept_manager_sees_only_own_department(client: TestClient, db_session: Session) -> None:
    dept_a, dept_b, position = make_org(db_session)
    manager_employee = make_employee(db_session, "E100", dept_a, position)
    make_employee(db_session, "E101", dept_a, position)
    make_employee(db_session, "E102", dept_b, position)
    db_session.commit()
    make_user(db_session, "6003", roles=["dept_manager"], employee_id=manager_employee.id)
    headers = auth_headers(client, "6003")

    resp = client.get("/api/v1/employees", headers=headers)

    assert resp.status_code == 200
    staff_nos = {e["staff_no"] for e in resp.json()}
    assert staff_nos == {"E100", "E101"}


def test_reviewer_sees_only_assigned_employees(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    assigned = make_employee(db_session, "E200", dept_a, position)
    make_employee(db_session, "E201", dept_a, position)
    db_session.commit()
    reviewer = make_user(db_session, "6004", roles=["reviewer"])
    db_session.add(EvaluationAssignment(employee_id=assigned.id, reviewer_user_id=reviewer.id))
    db_session.commit()
    headers = auth_headers(client, "6004")

    resp = client.get("/api/v1/employees", headers=headers)

    assert resp.status_code == 200
    staff_nos = {e["staff_no"] for e in resp.json()}
    assert staff_nos == {"E200"}


def test_employee_role_sees_only_self(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    self_employee = make_employee(db_session, "E300", dept_a, position)
    make_employee(db_session, "E301", dept_a, position)
    db_session.commit()
    make_user(db_session, "6005", roles=["employee"], employee_id=self_employee.id)
    headers = auth_headers(client, "6005")

    resp = client.get("/api/v1/employees", headers=headers)

    assert resp.status_code == 200
    staff_nos = {e["staff_no"] for e in resp.json()}
    assert staff_nos == {"E300"}

    forbidden = client.get(
        f"/api/v1/employees/{make_employee(db_session, 'E999', dept_a, position).id}",
        headers=headers,
    )
    assert forbidden.status_code == 403


def test_salary_hidden_from_reviewer(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    employee = make_employee(db_session, "E400", dept_a, position)
    db_session.commit()
    make_user(db_session, "6006", roles=["reviewer"])
    headers = auth_headers(client, "6006")

    resp = client.get(f"/api/v1/employees/{employee.id}/salaries", headers=headers)

    assert resp.status_code == 403


def test_salary_readable_by_hr_finance_pmo(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    employee = make_employee(db_session, "E401", dept_a, position)
    db_session.commit()
    make_user(db_session, "6007", roles=["hr"])
    headers = auth_headers(client, "6007")
    create = client.post(
        f"/api/v1/employees/{employee.id}/salaries",
        headers=headers,
        json={"effective_from": "2024-01-01", "base_salary": "5000"},
    )
    assert create.status_code == 201

    make_user(db_session, "6008", roles=["finance"])
    finance_headers = auth_headers(client, "6008")
    resp = client.get(f"/api/v1/employees/{employee.id}/salaries", headers=finance_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["base_salary"] == "5000.00"


def test_salary_write_forbidden_for_finance(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    employee = make_employee(db_session, "E402", dept_a, position)
    db_session.commit()
    make_user(db_session, "6009", roles=["finance"])
    headers = auth_headers(client, "6009")

    resp = client.post(
        f"/api/v1/employees/{employee.id}/salaries",
        headers=headers,
        json={"effective_from": "2024-01-01", "base_salary": "5000"},
    )

    assert resp.status_code == 403


def test_salary_overlap_rejected_with_409(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    employee = make_employee(db_session, "E403", dept_a, position)
    db_session.commit()
    make_user(db_session, "6010", roles=["hr"])
    headers = auth_headers(client, "6010")

    first = client.post(
        f"/api/v1/employees/{employee.id}/salaries",
        headers=headers,
        json={"effective_from": "2024-01-01", "base_salary": "5000"},
    )
    assert first.status_code == 201

    overlapping = client.post(
        f"/api/v1/employees/{employee.id}/salaries",
        headers=headers,
        json={"effective_from": "2024-06-01", "base_salary": "5500"},
    )
    assert overlapping.status_code == 409
    assert overlapping.json()["error"]["code"] == "salary_overlap"


def test_salary_as_of_boundaries(db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    employee = make_employee(db_session, "E404", dept_a, position)
    db_session.commit()
    make_user(db_session, "6011", roles=["hr"])
    db_session.add(
        EmployeeSalary(
            employee_id=employee.id,
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 4, 1),
            base_salary=5000,
        )
    )
    db_session.commit()

    assert service.salary_as_of(db_session, employee.id, date(2023, 12, 31)) is None
    assert service.salary_as_of(db_session, employee.id, date(2024, 1, 1)) is not None
    assert service.salary_as_of(db_session, employee.id, date(2024, 3, 31)) is not None
    assert service.salary_as_of(db_session, employee.id, date(2024, 4, 1)) is None


def test_assign_reviewer_forbidden_for_non_hr(client: TestClient, db_session: Session) -> None:
    dept_a, _, position = make_org(db_session)
    employee = make_employee(db_session, "E405", dept_a, position)
    reviewer = make_user(db_session, "6012", roles=["reviewer"])
    db_session.commit()
    make_user(db_session, "6013", roles=["dept_manager"])
    headers = auth_headers(client, "6013")

    resp = client.put(
        f"/api/v1/employees/{employee.id}/reviewer",
        headers=headers,
        json={"reviewer_user_id": reviewer.id},
    )

    assert resp.status_code == 403
