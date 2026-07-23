"""Phase 9 permissions penetration pass: a scripted matrix — every declaratively
role-gated endpoint (router-level `require_roles(...)`, plus the handful of
service-layer checks that are role-only, not ownership/state-dependent) x every
role in the system — asserting disallowed roles always get 403 and allowed
roles never do.

Deliberately excluded: endpoints whose access depends on *ownership or
workflow state* rather than role alone (e.g. `GET /evaluations/{id}`,
`GET /transfers/{id}`, `GET /incentive-runs/{id}`, any `/submit|/approve|
/return|/review` transition). Those are already exhaustively covered by each
module's own test file with real scoped/unscoped fixtures; duplicating them
here would just be noise. This file's job is narrower and complementary: prove
every *declarative* RBAC boundary in the app is wired correctly, in one place,
so a future endpoint added without a role gate — or with the wrong one — fails
loudly here instead of shipping silently.

An "allowed" role is only required to clear the gate (any non-403 status,
including a legitimate 400/404/409 from business logic) — this file does not
re-verify full success semantics, which is exactly what the per-module test
files are for.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.attendance.models import IncentivePeriod
from app.modules.auth.models import Role, User, UserRole
from app.modules.employees.models import Employee
from app.modules.incentives import service as incentives_service
from app.modules.kpi_templates.models import (
    KpiCriterion,
    KpiTemplate,
    KpiTemplateAssignment,
    KpiTemplateVersion,
)
from app.modules.org.models import Department, Position, PositionRate

PASSWORD = "InitialPass1"

ALL_ROLES = [
    "hr",
    "admin",
    "pmo",
    "factory_manager",
    "dept_manager",
    "reviewer",
    "finance",
    "key_person",
    "employee",
]

_ROLE_ABBR = {
    "hr": "HR",
    "admin": "AD",
    "pmo": "PM",
    "factory_manager": "FM",
    "dept_manager": "DM",
    "reviewer": "RV",
    "finance": "FI",
    "key_person": "KP",
    "employee": "EM",
}


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
    dept: Department
    dept_b: Department
    position: Position
    employee: Employee
    template: KpiTemplate
    version: KpiTemplateVersion
    criterion: KpiCriterion
    period: IncentivePeriod
    users: dict[str, User]
    victim_user: User
    run_id: int


def build_fixture(db_session: Session) -> Fixture:
    suffix = "PM1"
    dept = Department(code=f"MX{suffix}", name_en="Matrix Dept", name_ar="قسم المصفوفة")
    dept_b = Department(code=f"MXB{suffix}", name_en="Matrix Dept B", name_ar="قسم ب")
    position = Position(code=f"mxpos{suffix}", title_en="Matrix Pos", title_ar="وظيفة")
    db_session.add_all([dept, dept_b, position])
    db_session.flush()
    db_session.add(
        PositionRate(
            position_id=position.id, effective_from=date(2020, 1, 1), flat_ref_amount=Decimal(1000)
        )
    )

    template = KpiTemplate(
        code=f"MXTPL{suffix}", name_en="Matrix Template", name_ar="نموذج المصفوفة"
    )
    db_session.add(template)
    db_session.flush()
    version = KpiTemplateVersion(template_id=template.id, version_no=1, status="draft")
    db_session.add(version)
    db_session.flush()
    criterion = KpiCriterion(
        template_version_id=version.id,
        name_en="Output",
        name_ar="ناتج",
        max_marks=100,
        sort_order=1,
    )
    db_session.add(criterion)
    db_session.flush()
    db_session.add(
        KpiTemplateAssignment(
            position_id=position.id, template_id=template.id, effective_from=date(2020, 1, 1)
        )
    )

    employee = Employee(
        staff_no=f"MXEMP{suffix}",
        full_name_ar="اسم الموظف",
        department_id=dept.id,
        position_id=position.id,
    )
    db_session.add(employee)
    db_session.flush()

    period = IncentivePeriod(
        year=2040, month=1, target_pool=Decimal(1000), actual_pool=Decimal(800)
    )
    db_session.add(period)
    db_session.flush()

    users: dict[str, User] = {}
    for role in ALL_ROLES:
        staff_no = f"MX{_ROLE_ABBR[role]}{suffix}"
        if role == "dept_manager":
            mgr_employee = Employee(
                staff_no=f"MXDMEMP{suffix}",
                full_name_ar="مدير القسم",
                department_id=dept.id,
                position_id=position.id,
            )
            db_session.add(mgr_employee)
            db_session.flush()
            users[role] = make_user(db_session, staff_no, [role], employee_id=mgr_employee.id)
        elif role == "key_person":
            kp_employee = Employee(
                staff_no=f"MXKPEMP{suffix}",
                full_name_ar="موظف رئيسي",
                department_id=dept.id,
                position_id=position.id,
            )
            db_session.add(kp_employee)
            db_session.flush()
            users[role] = make_user(db_session, staff_no, [role], employee_id=kp_employee.id)
        else:
            users[role] = make_user(db_session, staff_no, [role])

    victim_user = make_user(db_session, f"MXVICTIM{suffix}", ["employee"])

    run = incentives_service.create_run(
        db_session, users["hr"], period_id=period.id, formula_mode="legacy_flat"
    )

    db_session.commit()
    return Fixture(
        dept=dept,
        dept_b=dept_b,
        position=position,
        employee=employee,
        template=template,
        version=version,
        criterion=criterion,
        period=period,
        run_id=run.id,
        users=users,
        victim_user=victim_user,
    )


@dataclass
class EndpointCheck:
    label: str
    method: str
    path: str
    allowed_roles: frozenset[str]
    json_body: dict | None = None


def build_matrix(fx: Fixture) -> list[EndpointCheck]:
    hr_pmo = frozenset({"hr", "pmo"})
    admin_hr = frozenset({"admin", "hr"})
    hr_only = frozenset({"hr"})
    pmo_only = frozenset({"pmo"})
    pmo_admin = frozenset({"pmo", "admin"})
    pmo_hr = frozenset({"pmo", "hr"})
    hr_pmo_admin = frozenset({"hr", "pmo", "admin"})
    hr_dm_admin = frozenset({"hr", "dept_manager", "admin"})
    rate_readers = frozenset({"hr", "finance", "pmo", "admin"})
    salary_readers = frozenset({"hr", "finance", "pmo"})
    finance_readers = frozenset({"hr", "pmo", "admin", "factory_manager", "finance"})
    template_downloaders = frozenset(
        {"hr", "pmo", "admin", "factory_manager", "dept_manager", "reviewer"}
    )
    key_person_only = frozenset({"key_person"})
    audit_readers = frozenset({"hr", "admin"})
    everyone = frozenset(ALL_ROLES)

    return [
        # ---- attendance -------------------------------------------------
        EndpointCheck(
            "create period", "POST", "/attendance/periods", hr_pmo, {"year": 2041, "month": 2}
        ),
        EndpointCheck(
            "lock period", "POST", f"/attendance/periods/{fx.period.id}/lock", hr_pmo, {}
        ),
        EndpointCheck(
            "unlock period", "POST", f"/attendance/periods/{fx.period.id}/unlock", hr_pmo, {}
        ),
        EndpointCheck(
            "update pools",
            "PATCH",
            f"/attendance/periods/{fx.period.id}/pools",
            pmo_only,
            {"target_pool": "1000", "actual_pool": "800"},
        ),
        # ---- users --------------------------------------------------------
        EndpointCheck("list users", "GET", "/users", admin_hr),
        EndpointCheck(
            "create user",
            "POST",
            "/users",
            admin_hr,
            {"staff_no": "MXNEWUSERPM1", "password": "InitialPass1!"},
        ),
        EndpointCheck(
            "patch user",
            "PATCH",
            f"/users/{fx.victim_user.id}",
            admin_hr,
            {"is_active": True},
        ),
        EndpointCheck(
            "assign roles",
            "PUT",
            f"/users/{fx.victim_user.id}/roles",
            hr_only,
            {"role_codes": ["employee"]},
        ),
        EndpointCheck(
            "reset password",
            "POST",
            f"/users/{fx.victim_user.id}/reset-password",
            hr_only,
            {"new_password": "NewPass123!"},
        ),
        EndpointCheck("list roles", "GET", "/roles", everyone),
        EndpointCheck("me", "GET", "/auth/me", everyone),
        EndpointCheck(
            # deliberately wrong current_password: this must 400, never actually
            # change anything — a real password change here would break every
            # later auth_headers() call for that role in this same test run.
            "change password",
            "POST",
            "/auth/change-password",
            everyone,
            {"current_password": "definitely-wrong", "new_password": "SomeOtherPass1!"},
        ),
        # ---- org ------------------------------------------------------------
        EndpointCheck("list departments", "GET", "/departments", everyone),
        EndpointCheck(
            "create department",
            "POST",
            "/departments",
            hr_only,
            {"code": "MXDPM1", "name_en": "X", "name_ar": "س"},
        ),
        EndpointCheck(
            "patch department", "PATCH", f"/departments/{fx.dept.id}", hr_only, {"name_en": "Y"}
        ),
        EndpointCheck("list positions", "GET", "/positions", everyone),
        EndpointCheck(
            "create position",
            "POST",
            "/positions",
            hr_only,
            {"code": "MXPPM1", "title_en": "X", "title_ar": "و"},
        ),
        EndpointCheck(
            "patch position", "PATCH", f"/positions/{fx.position.id}", hr_only, {"title_en": "Y"}
        ),
        EndpointCheck(
            "list position rates", "GET", f"/positions/{fx.position.id}/rates", rate_readers
        ),
        EndpointCheck(
            "create position rate",
            "POST",
            f"/positions/{fx.position.id}/rates",
            hr_only,
            {"effective_from": "2031-01-01", "flat_ref_amount": "500"},
        ),
        # ---- employees ------------------------------------------------------
        EndpointCheck("list employees", "GET", "/employees", everyone),
        EndpointCheck(
            "create employee",
            "POST",
            "/employees",
            hr_only,
            {
                "staff_no": "MXNEWEMPPM1",
                "full_name_ar": "اسم جديد",
                "department_id": fx.dept.id,
                "position_id": fx.position.id,
            },
        ),
        EndpointCheck(
            "patch employee",
            "PATCH",
            f"/employees/{fx.employee.id}",
            hr_only,
            {"full_name_ar": "اسم معدل"},
        ),
        EndpointCheck(
            "assign reviewer",
            "PUT",
            f"/employees/{fx.employee.id}/reviewer",
            hr_only,
            {"reviewer_user_id": fx.users["reviewer"].id},
        ),
        EndpointCheck(
            "list salaries", "GET", f"/employees/{fx.employee.id}/salaries", salary_readers
        ),
        EndpointCheck(
            "create salary",
            "POST",
            f"/employees/{fx.employee.id}/salaries",
            hr_only,
            {"effective_from": "2020-01-01", "base_salary": "3000"},
        ),
        # ---- kpi templates ----------------------------------------------------
        EndpointCheck("list templates", "GET", "/kpi-templates", everyone),
        EndpointCheck(
            "create template",
            "POST",
            "/kpi-templates",
            pmo_admin,
            {"code": "MXKTPM1", "name_en": "X", "name_ar": "ص"},
        ),
        EndpointCheck("get template", "GET", f"/kpi-templates/{fx.template.id}", everyone),
        EndpointCheck(
            "list versions", "GET", f"/kpi-templates/{fx.template.id}/versions", everyone
        ),
        EndpointCheck(
            "clone version", "POST", f"/kpi-templates/{fx.template.id}/versions", pmo_admin, {}
        ),
        EndpointCheck("get version", "GET", f"/kpi-templates/versions/{fx.version.id}", everyone),
        EndpointCheck(
            "activate version",
            "POST",
            f"/kpi-templates/versions/{fx.version.id}/activate",
            pmo_admin,
            {},
        ),
        EndpointCheck(
            "create criterion",
            "POST",
            f"/kpi-templates/versions/{fx.version.id}/criteria",
            pmo_admin,
            {
                "name_en": "C2",
                "name_ar": "م2",
                "max_marks": 10,
                "input_mode": "marks",
                "allow_negative": False,
                "auto_source": "none",
                "auto_params": None,
                "sort_order": 2,
            },
        ),
        EndpointCheck(
            "patch criterion",
            "PATCH",
            f"/kpi-templates/criteria/{fx.criterion.id}",
            pmo_admin,
            {"max_marks": 50},
        ),
        EndpointCheck(
            "delete criterion", "DELETE", f"/kpi-templates/criteria/{fx.criterion.id}", pmo_admin
        ),
        EndpointCheck(
            "list assignments",
            "GET",
            f"/positions/{fx.position.id}/kpi-template-assignments",
            everyone,
        ),
        EndpointCheck(
            "create assignment",
            "POST",
            f"/positions/{fx.position.id}/kpi-template-assignments",
            pmo_hr,
            {"template_id": fx.template.id, "effective_from": "2036-01-01"},
        ),
        # ---- evaluations ------------------------------------------------------
        EndpointCheck("list evaluations", "GET", "/evaluations", everyone),
        EndpointCheck(
            "create evaluation",
            "POST",
            "/evaluations",
            hr_pmo_admin,
            {"employee_id": fx.employee.id, "period_id": fx.period.id, "kind": "regular"},
        ),
        EndpointCheck(
            "create self appraisal",
            "POST",
            "/evaluations/self",
            key_person_only,
            {"period_id": fx.period.id},
        ),
        EndpointCheck(
            "bulk create evaluations",
            "POST",
            "/evaluations/bulk",
            hr_pmo_admin,
            {"department_id": fx.dept.id, "period_id": fx.period.id, "kind": "regular"},
        ),
        # ---- transfers ----------------------------------------------------------
        EndpointCheck("list transfers", "GET", "/transfers", everyone),
        EndpointCheck(
            "create transfer",
            "POST",
            "/transfers",
            hr_dm_admin,
            {
                "employee_id": fx.employee.id,
                "to_department_id": fx.dept_b.id,
                "effective_date": "2040-06-01",
            },
        ),
        # ---- incentive runs ---------------------------------------------------
        EndpointCheck("list incentive runs", "GET", "/incentive-runs", everyone),
        EndpointCheck(
            "create incentive run",
            "POST",
            "/incentive-runs",
            hr_pmo_admin,
            {"period_id": fx.period.id, "formula_mode": "legacy_flat"},
        ),
        EndpointCheck("my incentives", "GET", "/incentive-runs/my/incentives", everyone),
        # ---- reports ------------------------------------------------------------
        EndpointCheck(
            "period summary", "GET", f"/reports/periods/{fx.period.id}/summary", finance_readers
        ),
        EndpointCheck(
            "finance excel", "GET", f"/reports/runs/{fx.run_id}/finance-excel", finance_readers
        ),
        EndpointCheck(
            "finance pdf", "GET", f"/reports/runs/{fx.run_id}/finance-pdf", finance_readers
        ),
        EndpointCheck(
            "blank template excel",
            "GET",
            f"/reports/kpi-templates/{fx.version.id}/blank-excel",
            template_downloaders,
        ),
        EndpointCheck(
            "blank template pdf",
            "GET",
            f"/reports/kpi-templates/{fx.version.id}/blank-pdf",
            template_downloaders,
        ),
        # ---- audit --------------------------------------------------------------
        EndpointCheck("list audit log", "GET", "/audit-log", audit_readers),
    ]


def test_permissions_matrix(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session)
    checks = build_matrix(fx)

    failures: list[str] = []
    for check in checks:
        for role in ALL_ROLES:
            headers = auth_headers(client, fx.users[role].staff_no)
            resp = client.request(
                check.method, f"/api/v1{check.path}", headers=headers, json=check.json_body
            )
            if role in check.allowed_roles:
                if resp.status_code == 403:
                    failures.append(
                        f"[{check.label}] {check.method} {check.path}: "
                        f"role '{role}' should be allowed but got 403"
                    )
            else:
                if resp.status_code != 403:
                    failures.append(
                        f"[{check.label}] {check.method} {check.path}: "
                        f"role '{role}' should be forbidden but got {resp.status_code}"
                    )

    assert not failures, "Permissions matrix gaps found:\n" + "\n".join(failures)


def test_finance_reports_forbidden_when_run_not_yet_approved_is_still_role_gated(
    client: TestClient, db_session: Session
) -> None:
    """A 400 run_not_approved must still only be reachable by FinanceReaders —
    proves the role gate runs before the business-rule check, not after."""
    fx = build_fixture(db_session)
    created = client.post(
        "/api/v1/incentive-runs",
        headers=auth_headers(client, fx.users["hr"].staff_no),
        json={"period_id": fx.period.id, "formula_mode": "legacy_flat"},
    ).json()

    forbidden_resp = client.get(
        f"/api/v1/reports/runs/{created['id']}/finance-excel",
        headers=auth_headers(client, fx.users["reviewer"].staff_no),
    )
    assert forbidden_resp.status_code == 403

    allowed_resp = client.get(
        f"/api/v1/reports/runs/{created['id']}/finance-excel",
        headers=auth_headers(client, fx.users["finance"].staff_no),
    )
    assert allowed_resp.status_code == 400
    assert allowed_resp.json()["error"]["code"] == "run_not_approved"
