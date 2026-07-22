from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.attendance.models import AttendanceImport, AttendanceRecord, IncentivePeriod
from app.modules.auth.models import Role, User, UserRole
from app.modules.employees.models import Employee, EvaluationAssignment
from app.modules.evaluations import service as evaluations_service
from app.modules.evaluations.service import ScoreUpdateInput
from app.modules.kpi_templates.models import (
    KpiCriterion,
    KpiTemplate,
    KpiTemplateAssignment,
    KpiTemplateVersion,
)
from app.modules.org.models import Department, Position, PositionRate

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


def _get_or_create_period(
    db_session: Session, *, year: int = 2031, month: int = 1
) -> IncentivePeriod:
    period = db_session.scalars(
        select(IncentivePeriod).where(
            IncentivePeriod.year == year, IncentivePeriod.month == month
        )
    ).first()
    if period is None:
        period = IncentivePeriod(
            year=year, month=month, target_pool=Decimal(1000), actual_pool=Decimal(800)
        )
        db_session.add(period)
        db_session.flush()
    return period


def _get_or_create_import(db_session: Session, period_id: int, uploader_id: int) -> int:
    existing = db_session.scalars(
        select(AttendanceImport).where(
            AttendanceImport.period_id == period_id, AttendanceImport.status == "active"
        )
    ).first()
    if existing is not None:
        return existing.id
    imp = AttendanceImport(
        period_id=period_id,
        file_sha256="0" * 64,
        original_filename="x.xlsx",
        uploaded_by_user_id=uploader_id,
        row_count=1,
        status="active",
    )
    db_session.add(imp)
    db_session.flush()
    return imp.id


@dataclass
class Fixture:
    dept: Department
    position: Position
    template: KpiTemplate
    version: KpiTemplateVersion
    criterion: KpiCriterion
    period: IncentivePeriod
    employee: Employee
    hr: User
    pmo: User
    fm: User
    reviewer: User
    dept_manager: User


def build_fixture(db_session: Session, *, suffix: str) -> Fixture:
    dept = Department(code=f"RD{suffix}", name_en=f"Reports Dept {suffix}", name_ar="قسم الإنتاج")
    position = Position(code=f"rpos{suffix}", title_en=f"Pos {suffix}", title_ar="وظيفة")
    db_session.add_all([dept, position])
    db_session.flush()
    db_session.add(
        PositionRate(
            position_id=position.id, effective_from=date(2020, 1, 1), flat_ref_amount=Decimal(1000)
        )
    )

    template = KpiTemplate(code=f"RTPL{suffix}", name_en="Skilled", name_ar="نموذج المهرة")
    db_session.add(template)
    db_session.flush()
    version = KpiTemplateVersion(template_id=template.id, version_no=1, status="active")
    db_session.add(version)
    db_session.flush()
    criterion = KpiCriterion(
        template_version_id=version.id,
        name_en="Quality",
        name_ar="الجودة",
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
        staff_no=f"REMP{suffix}",
        full_name_ar="اسم الموظف",
        full_name_en=f"Employee {suffix}",
        department_id=dept.id,
        position_id=position.id,
    )
    db_session.add(employee)
    db_session.flush()

    period = _get_or_create_period(db_session)

    hr = make_user(db_session, f"RHR{suffix}", roles=["hr"])
    pmo = make_user(db_session, f"RPMO{suffix}", roles=["pmo"])
    fm = make_user(db_session, f"RFM{suffix}", roles=["factory_manager"])
    reviewer = make_user(db_session, f"RREV{suffix}", roles=["reviewer"])
    mgr_employee = Employee(
        staff_no=f"RMGR{suffix}",
        full_name_ar="مدير",
        department_id=dept.id,
        position_id=position.id,
    )
    db_session.add(mgr_employee)
    db_session.flush()
    dept_manager = make_user(
        db_session, f"RDM{suffix}", roles=["dept_manager"], employee_id=mgr_employee.id
    )
    db_session.add(EvaluationAssignment(employee_id=employee.id, reviewer_user_id=reviewer.id))
    db_session.commit()

    evaluation = evaluations_service.create_evaluation(
        db_session, hr, employee_id=employee.id, period_id=period.id, kind="regular"
    )
    evaluation = evaluations_service.update_evaluation_scores(
        db_session,
        reviewer,
        evaluation.id,
        expected_row_version=evaluation.row_version,
        score_updates=[ScoreUpdateInput(criterion_id=criterion.id, raw_input=Decimal(90))],
        activities=None,
    )
    evaluations_service.perform_transition(db_session, reviewer, evaluation.id, action="submit")
    evaluations_service.perform_transition(
        db_session, dept_manager, evaluation.id, action="approve"
    )

    db_session.add(
        AttendanceRecord(
            period_id=period.id,
            employee_id=employee.id,
            import_id=_get_or_create_import(db_session, period.id, hr.id),
            present=25,
            off_days=2,
            absent=0,
            leave=0,
            public_holiday=0,
            deduct_min=0,
            over_time=0,
            approved=25,
            pending_approval=0,
            submitted=0,
            approved_over_time=0,
        )
    )
    db_session.commit()

    return Fixture(
        dept=dept,
        position=position,
        template=template,
        version=version,
        criterion=criterion,
        period=period,
        employee=employee,
        hr=hr,
        pmo=pmo,
        fm=fm,
        reviewer=reviewer,
        dept_manager=dept_manager,
    )


def create_and_approve_run(client: TestClient, fx: Fixture) -> dict:
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)

    created = client.post(
        "/api/v1/incentive-runs",
        headers=hr_headers,
        json={"period_id": fx.period.id, "formula_mode": "legacy_flat"},
    ).json()
    run_id = created["id"]
    client.post(f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/complete-audit", headers=pmo_headers, json={})
    approved = client.post(f"/api/v1/incentive-runs/{run_id}/approve", headers=fm_headers, json={})
    return approved.json()


# ---- period summary ---------------------------------------------------------


def test_period_summary_empty_before_any_approved_run(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="1")

    resp = client.get(
        f"/api/v1/reports/periods/{fx.period.id}/summary",
        headers=auth_headers(client, fx.hr.staff_no),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] is None
    assert body["departments"] == []
    assert Decimal(body["grand_total"]) == Decimal(0)


def test_period_summary_reflects_approved_run(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="2")
    run = create_and_approve_run(client, fx)
    assert run["status"] == "approved"

    resp = client.get(
        f"/api/v1/reports/periods/{fx.period.id}/summary",
        headers=auth_headers(client, fx.hr.staff_no),
    )

    body = resp.json()
    assert body["run_id"] == run["id"]
    dept_entry = next(d for d in body["departments"] if d["code"] == fx.dept.code)
    assert dept_entry["employee_count"] == 1
    assert Decimal(dept_entry["total_amount"]) == Decimal(run["total_final_amount"])
    assert Decimal(body["grand_total"]) == Decimal(run["total_final_amount"])


# ---- finance excel/pdf -------------------------------------------------------


def test_finance_excel_requires_approved_run(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="3")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    created = client.post(
        "/api/v1/incentive-runs",
        headers=hr_headers,
        json={"period_id": fx.period.id, "formula_mode": "legacy_flat"},
    ).json()

    resp = client.get(f"/api/v1/reports/runs/{created['id']}/finance-excel", headers=hr_headers)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "run_not_approved"


def test_finance_excel_download_succeeds_for_approved_run(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="4")
    run = create_and_approve_run(client, fx)

    resp = client.get(
        f"/api/v1/reports/runs/{run['id']}/finance-excel",
        headers=auth_headers(client, fx.hr.staff_no),
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert resp.content[:2] == b"PK"  # xlsx is a zip archive


def test_finance_excel_forbidden_for_reviewer(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="5")
    run = create_and_approve_run(client, fx)

    resp = client.get(
        f"/api/v1/reports/runs/{run['id']}/finance-excel",
        headers=auth_headers(client, fx.reviewer.staff_no),
    )

    assert resp.status_code == 403


def test_finance_pdf_download_succeeds_for_approved_run(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="6")
    run = create_and_approve_run(client, fx)

    resp = client.get(
        f"/api/v1/reports/runs/{run['id']}/finance-pdf",
        headers=auth_headers(client, fx.hr.staff_no),
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


# ---- blank evaluation templates ----------------------------------------------


def test_blank_excel_download_includes_real_roster(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="7")

    resp = client.get(
        f"/api/v1/reports/kpi-templates/{fx.version.id}/blank-excel",
        headers=auth_headers(client, fx.dept_manager.staff_no),
    )

    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"


def test_blank_pdf_download_succeeds(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="8")

    resp = client.get(
        f"/api/v1/reports/kpi-templates/{fx.version.id}/blank-pdf",
        headers=auth_headers(client, fx.reviewer.staff_no),
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_blank_template_forbidden_for_plain_employee(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="9")
    employee_user = make_user(
        db_session, "RPLAIN9", roles=["employee"], employee_id=fx.employee.id
    )

    resp = client.get(
        f"/api/v1/reports/kpi-templates/{fx.version.id}/blank-excel",
        headers=auth_headers(client, employee_user.staff_no),
    )

    assert resp.status_code == 403
