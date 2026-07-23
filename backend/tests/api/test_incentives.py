from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.attendance.models import AttendanceImport, AttendanceRecord, IncentivePeriod
from app.modules.auth.models import Role, User, UserRole
from app.modules.employees.models import Employee, EmployeeSalary, EvaluationAssignment
from app.modules.evaluations import service as evaluations_service
from app.modules.evaluations.models import Evaluation
from app.modules.evaluations.service import ScoreUpdateInput
from app.modules.incentives import service as incentives_service
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


def _get_or_create_period(
    db_session: Session, *, year: int = 2030, month: int = 1
) -> IncentivePeriod:
    period = db_session.scalars(
        select(IncentivePeriod).where(
            IncentivePeriod.year == year, IncentivePeriod.month == month
        )
    ).first()
    if period is None:
        period = IncentivePeriod(year=year, month=month)
        db_session.add(period)
        db_session.flush()
    return period


@dataclass
class Fixture:
    dept: Department
    position: Position
    criterion: KpiCriterion
    period: IncentivePeriod
    employee: Employee
    hr: User
    pmo: User
    fm: User
    dept_manager: User
    reviewer: User
    evaluation: Evaluation | None


def build_fixture(
    db_session: Session,
    *,
    suffix: str,
    score_pct: Decimal = Decimal("0.9"),
    flat_ref_amount: Decimal | None = Decimal(1000),
    position_incentive_pct: Decimal | None = None,
    target_pool: Decimal = Decimal(1000),
    actual_pool: Decimal = Decimal(800),
    with_attendance: bool = True,
    with_evaluation: bool = True,
    employment_status: str = "active",
) -> Fixture:
    dept = Department(code=f"ID{suffix}", name_en=f"Inc Dept {suffix}", name_ar="قسم")
    position = Position(code=f"ipos{suffix}", title_en=f"Pos {suffix}", title_ar="وظيفة")
    db_session.add_all([dept, position])
    db_session.flush()
    db_session.add(
        PositionRate(
            position_id=position.id,
            effective_from=date(2020, 1, 1),
            flat_ref_amount=flat_ref_amount,
            incentive_pct=position_incentive_pct,
        )
    )

    template = KpiTemplate(code=f"ITPL{suffix}", name_en="Template", name_ar="نموذج")
    db_session.add(template)
    db_session.flush()
    version = KpiTemplateVersion(template_id=template.id, version_no=1, status="active")
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
        staff_no=f"IEMP{suffix}",
        full_name_ar="اسم الموظف",
        department_id=dept.id,
        position_id=position.id,
        employment_status=employment_status,
    )
    db_session.add(employee)
    db_session.flush()

    period = _get_or_create_period(db_session)
    if period.target_pool is None:
        period.target_pool = target_pool
        period.actual_pool = actual_pool

    hr = make_user(db_session, f"IHR{suffix}", roles=["hr"])
    pmo = make_user(db_session, f"IPMO{suffix}", roles=["pmo"])
    fm = make_user(db_session, f"IFM{suffix}", roles=["factory_manager"])
    mgr_employee = Employee(
        staff_no=f"IMGR{suffix}",
        full_name_ar="مدير",
        department_id=dept.id,
        position_id=position.id,
    )
    db_session.add(mgr_employee)
    db_session.flush()
    dept_manager = make_user(
        db_session, f"IDM{suffix}", roles=["dept_manager"], employee_id=mgr_employee.id
    )
    reviewer = make_user(db_session, f"IREV{suffix}", roles=["reviewer"])
    db_session.add(EvaluationAssignment(employee_id=employee.id, reviewer_user_id=reviewer.id))
    db_session.commit()

    evaluation = None
    if with_evaluation:
        evaluation = evaluations_service.create_evaluation(
            db_session, hr, employee_id=employee.id, period_id=period.id, kind="regular"
        )
        evaluation = evaluations_service.update_evaluation_scores(
            db_session,
            reviewer,
            evaluation.id,
            expected_row_version=evaluation.row_version,
            score_updates=[
                ScoreUpdateInput(criterion_id=criterion.id, raw_input=score_pct * Decimal(100))
            ],
            activities=None,
        )
        evaluations_service.perform_transition(db_session, reviewer, evaluation.id, action="submit")
        evaluation = evaluations_service.perform_transition(
            db_session, dept_manager, evaluation.id, action="approve"
        )

    if with_attendance:
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
        criterion=criterion,
        period=period,
        employee=employee,
        hr=hr,
        pmo=pmo,
        fm=fm,
        dept_manager=dept_manager,
        reviewer=reviewer,
        evaluation=evaluation,
    )


def create_run(
    client: TestClient,
    fx: Fixture,
    *,
    formula_mode: str = "legacy_flat",
    requester: User | None = None,
):
    actor = requester or fx.hr
    return client.post(
        "/api/v1/incentive-runs",
        headers=auth_headers(client, actor.staff_no),
        json={"period_id": fx.period.id, "formula_mode": formula_mode},
    )


# ---- run creation: happy path + exceptions ---------------------------------


def test_create_run_computes_line_matching_the_engine(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(
        db_session, suffix="1", score_pct=Decimal("0.9"), flat_ref_amount=Decimal(1000)
    )

    resp = create_run(client, fx)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert len(body["lines"]) == 1
    line = body["lines"][0]
    assert line["employee"]["id"] == fx.employee.id
    assert Decimal(line["evaluation_pct"]) == Decimal("0.9000")
    assert Decimal(line["flat_ref_amount"]) == Decimal("1000.00")
    # 0.9 * 1000 * 1.00 * (800/1000=0.8) = 720 -> ceil10 = 720
    assert Decimal(line["computed_amount"]) == Decimal("720.00")
    assert Decimal(line["final_amount"]) == Decimal("720.00")
    # the fixture's own dept-manager employee has no evaluation of its own —
    # it legitimately shows up as its own exception rather than being silently
    # dropped; only assert about fx.employee here.
    assert not any(e["employee_id"] == fx.employee.id for e in body["exceptions"])


def test_create_run_exception_missing_evaluation(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="2", with_evaluation=False)

    resp = create_run(client, fx)

    assert resp.status_code == 201
    body = resp.json()
    assert body["lines"] == []
    exception = next(e for e in body["exceptions"] if e["employee_id"] == fx.employee.id)
    assert exception == {
        "employee_id": fx.employee.id,
        "staff_no": fx.employee.staff_no,
        "reason": "missing_evaluation",
    }


def test_create_run_exception_missing_attendance(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="3", with_attendance=False)

    resp = create_run(client, fx)

    exception = next(e for e in resp.json()["exceptions"] if e["employee_id"] == fx.employee.id)
    assert exception["reason"] == "missing_attendance"


def test_create_run_exception_inactive_employee(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="4", employment_status="terminated")

    resp = create_run(client, fx)

    exception = next(e for e in resp.json()["exceptions"] if e["employee_id"] == fx.employee.id)
    assert exception["reason"] == "inactive"


def test_create_run_exception_missing_salary_for_pct_mode(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="5", position_incentive_pct=Decimal("0.15"))

    resp = create_run(client, fx, formula_mode="pct_of_salary")

    exception = next(
        e for e in resp.json()["exceptions"] if e["employee_id"] == fx.employee.id
    )
    assert exception["reason"] == "missing_salary"


def test_create_run_pct_of_salary_mode_happy_path(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(
        db_session, suffix="6", score_pct=Decimal("0.9"), position_incentive_pct=Decimal("0.15")
    )
    db_session.add(
        EmployeeSalary(
            employee_id=fx.employee.id, effective_from=date(2020, 1, 1), base_salary=Decimal(2000)
        )
    )
    db_session.commit()

    resp = create_run(client, fx, formula_mode="pct_of_salary")

    assert resp.status_code == 201
    line = resp.json()["lines"][0]
    # 0.9 * (2000*0.15=300) * 1 * 0.8 = 216 -> ceil10 = 220
    assert Decimal(line["computed_amount"]) == Decimal("220.00")


def test_create_run_requires_pools_set(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="7")
    fx.period.target_pool = None
    fx.period.actual_pool = None
    db_session.commit()

    resp = create_run(client, fx)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "pools_not_set"


def test_create_run_requires_hr_pmo_or_admin(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="8")

    resp = create_run(client, fx, requester=fx.reviewer)

    assert resp.status_code == 403


# ---- scoping ----------------------------------------------------------------


def test_dept_manager_sees_only_own_department_lines(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="9")
    run_id = create_run(client, fx).json()["id"]

    resp = client.get(
        f"/api/v1/incentive-runs/{run_id}", headers=auth_headers(client, fx.dept_manager.staff_no)
    )
    assert resp.status_code == 200
    assert len(resp.json()["lines"]) == 1

    other_fx = build_fixture(db_session, suffix="10")
    resp2 = client.get(
        f"/api/v1/incentive-runs/{run_id}",
        headers=auth_headers(client, other_fx.dept_manager.staff_no),
    )
    assert resp2.status_code == 200
    assert resp2.json()["lines"] == []


def test_unrelated_role_forbidden_from_viewing_run(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="11")
    run_id = create_run(client, fx).json()["id"]

    resp = client.get(
        f"/api/v1/incentive-runs/{run_id}", headers=auth_headers(client, fx.reviewer.staff_no)
    )
    assert resp.status_code == 403


def test_list_runs_omits_runs_an_unrelated_role_cannot_see(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="11b")
    create_run(client, fx)

    resp = client.get(
        "/api/v1/incentive-runs", headers=auth_headers(client, fx.reviewer.staff_no)
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_runs_scopes_lines_and_total_for_dept_manager(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="11c")
    run = create_run(client, fx).json()

    resp = client.get(
        "/api/v1/incentive-runs", headers=auth_headers(client, fx.dept_manager.staff_no)
    )
    assert resp.status_code == 200
    listed = next(r for r in resp.json() if r["id"] == run["id"])
    assert len(listed["lines"]) == 1
    assert listed["total_final_amount"] == run["total_final_amount"]

    other_fx = build_fixture(db_session, suffix="11d")
    resp2 = client.get(
        "/api/v1/incentive-runs", headers=auth_headers(client, other_fx.dept_manager.staff_no)
    )
    listed2 = next(r for r in resp2.json() if r["id"] == run["id"])
    assert listed2["lines"] == []
    assert Decimal(listed2["total_final_amount"]) == Decimal(0)


def test_dept_manager_with_no_linked_employee_is_forbidden_not_empty(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="11g")
    run_id = create_run(client, fx).json()["id"]
    unlinked_manager = make_user(db_session, "IDM11G", roles=["dept_manager"])

    detail_resp = client.get(
        f"/api/v1/incentive-runs/{run_id}", headers=auth_headers(client, unlinked_manager.staff_no)
    )
    assert detail_resp.status_code == 403

    list_resp = client.get(
        "/api/v1/incentive-runs", headers=auth_headers(client, unlinked_manager.staff_no)
    )
    assert list_resp.status_code == 200
    assert all(r["id"] != run_id for r in list_resp.json())


def test_full_access_role_sees_every_run_in_list(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="11e")
    run = create_run(client, fx).json()

    resp = client.get("/api/v1/incentive-runs", headers=auth_headers(client, fx.pmo.staff_no))
    assert resp.status_code == 200
    listed = next(r for r in resp.json() if r["id"] == run["id"])
    assert len(listed["lines"]) == 1


def test_finance_role_has_full_access_matching_its_export_rights(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="11f")
    run = create_run(client, fx).json()
    finance_user = make_user(db_session, "IFIN11F", roles=["finance"])

    list_resp = client.get(
        "/api/v1/incentive-runs", headers=auth_headers(client, finance_user.staff_no)
    )
    assert list_resp.status_code == 200
    listed = next(r for r in list_resp.json() if r["id"] == run["id"])
    assert len(listed["lines"]) == 1

    detail_resp = client.get(
        f"/api/v1/incentive-runs/{run['id']}", headers=auth_headers(client, finance_user.staff_no)
    )
    assert detail_resp.status_code == 200


# ---- line editing (draft only) -----------------------------------------------


def test_update_line_attendance_factor_recomputes(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="12")
    run = create_run(client, fx).json()
    line = run["lines"][0]

    resp = client.patch(
        f"/api/v1/incentive-runs/{run['id']}/lines/{line['id']}",
        headers=auth_headers(client, fx.hr.staff_no),
        json={"row_version": line["row_version"], "attendance_factor": "0.5"},
    )
    assert resp.status_code == 200
    updated = next(item for item in resp.json()["lines"] if item["id"] == line["id"])
    # 0.9 * 1000 * 0.5 * 0.8 = 360
    assert Decimal(updated["computed_amount"]) == Decimal("360.00")
    assert Decimal(updated["final_amount"]) == Decimal("360.00")
    assert updated["row_version"] == line["row_version"] + 1


def test_update_line_override_requires_reason(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="13")
    run = create_run(client, fx).json()
    line = run["lines"][0]

    resp = client.patch(
        f"/api/v1/incentive-runs/{run['id']}/lines/{line['id']}",
        headers=auth_headers(client, fx.hr.staff_no),
        json={"row_version": line["row_version"], "override_amount": "500"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "override_reason_required"


def test_update_line_override_sets_final_amount(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="14")
    run = create_run(client, fx).json()
    line = run["lines"][0]

    resp = client.patch(
        f"/api/v1/incentive-runs/{run['id']}/lines/{line['id']}",
        headers=auth_headers(client, fx.hr.staff_no),
        json={
            "row_version": line["row_version"],
            "override_amount": "500",
            "override_reason": "manual adjustment",
        },
    )
    assert resp.status_code == 200
    updated = next(item for item in resp.json()["lines"] if item["id"] == line["id"])
    assert Decimal(updated["final_amount"]) == Decimal("500.00")
    assert Decimal(updated["computed_amount"]) == Decimal("720.00")  # engine output untouched


def test_update_line_exclude_requires_reason(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="15")
    run = create_run(client, fx).json()
    line = run["lines"][0]

    resp = client.patch(
        f"/api/v1/incentive-runs/{run['id']}/lines/{line['id']}",
        headers=auth_headers(client, fx.hr.staff_no),
        json={"row_version": line["row_version"], "is_excluded": True},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "exclude_reason_required"


def test_update_line_stale_row_version_conflicts(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="16")
    run = create_run(client, fx).json()
    line = run["lines"][0]

    resp = client.patch(
        f"/api/v1/incentive-runs/{run['id']}/lines/{line['id']}",
        headers=auth_headers(client, fx.hr.staff_no),
        json={"row_version": line["row_version"] + 99, "attendance_factor": "0.5"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "row_version_conflict"


def test_recalculate_recomputes_all_non_excluded_lines(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="17")
    run_id = create_run(client, fx).json()["id"]
    line = client.get(
        f"/api/v1/incentive-runs/{run_id}", headers=auth_headers(client, fx.hr.staff_no)
    ).json()["lines"][0]
    client.patch(
        f"/api/v1/incentive-runs/{run_id}/lines/{line['id']}",
        headers=auth_headers(client, fx.hr.staff_no),
        json={"row_version": line["row_version"], "is_excluded": True, "exclude_reason": "test"},
    )

    resp = client.post(
        f"/api/v1/incentive-runs/{run_id}/recalculate", headers=auth_headers(client, fx.hr.staff_no)
    )
    assert resp.status_code == 200


# ---- transition matrix + period lock ---------------------------------------


def test_full_workflow_locks_period_on_approval(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="18")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)
    run_id = create_run(client, fx).json()["id"]

    submitted = client.post(
        f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={}
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "pmo_audit"

    audited = client.post(
        f"/api/v1/incentive-runs/{run_id}/complete-audit", headers=pmo_headers, json={}
    )
    assert audited.status_code == 200
    assert audited.json()["status"] == "fm_approval"

    approved = client.post(f"/api/v1/incentive-runs/{run_id}/approve", headers=fm_headers, json={})
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    period = client.get(
        f"/api/v1/attendance/periods/{fx.period.id}", headers=hr_headers
    ).json()
    assert period["status"] == "locked"


def test_reject_returns_run_to_draft(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="19")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    run_id = create_run(client, fx).json()["id"]
    client.post(f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={})

    rejected = client.post(
        f"/api/v1/incentive-runs/{run_id}/reject",
        headers=pmo_headers,
        json={"comment": "needs fixing"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "draft"


def test_complete_audit_forbidden_for_non_pmo(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="20")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    run_id = create_run(client, fx).json()["id"]
    client.post(f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={})

    resp = client.post(
        f"/api/v1/incentive-runs/{run_id}/complete-audit", headers=hr_headers, json={}
    )
    assert resp.status_code == 403


def test_only_one_run_can_reach_approved_per_period(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="21")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)

    def approve_new_run() -> int:
        rid = create_run(client, fx).json()["id"]
        client.post(f"/api/v1/incentive-runs/{rid}/submit-audit", headers=hr_headers, json={})
        client.post(f"/api/v1/incentive-runs/{rid}/complete-audit", headers=pmo_headers, json={})
        return rid

    first_run_id = approve_new_run()
    first_approved = client.post(
        f"/api/v1/incentive-runs/{first_run_id}/approve", headers=fm_headers, json={}
    )
    assert first_approved.status_code == 200

    second_run_id = approve_new_run()
    second_approved = client.post(
        f"/api/v1/incentive-runs/{second_run_id}/approve", headers=fm_headers, json={}
    )
    assert second_approved.status_code == 409
    assert second_approved.json()["error"]["code"] == "period_already_has_approved_run"


def test_locked_period_blocks_evaluation_edits(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="22")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)
    run_id = create_run(client, fx).json()["id"]
    client.post(f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/complete-audit", headers=pmo_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/approve", headers=fm_headers, json={})

    resp = client.post(
        "/api/v1/evaluations",
        headers=hr_headers,
        json={"employee_id": fx.employee.id, "period_id": fx.period.id, "kind": "self_appraisal"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "period_locked"


def test_locked_period_blocks_pool_edits_and_manual_unlock(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="23")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)
    run_id = create_run(client, fx).json()["id"]
    client.post(f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/complete-audit", headers=pmo_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/approve", headers=fm_headers, json={})

    pool_resp = client.patch(
        f"/api/v1/attendance/periods/{fx.period.id}/pools",
        headers=pmo_headers,
        json={"target_pool": "999", "actual_pool": "999"},
    )
    assert pool_resp.status_code == 409
    assert pool_resp.json()["error"]["code"] == "period_locked"

    unlock_resp = client.post(
        f"/api/v1/attendance/periods/{fx.period.id}/unlock", headers=hr_headers
    )
    assert unlock_resp.status_code == 409
    assert unlock_resp.json()["error"]["code"] == "period_has_approved_run"


def test_submit_audit_rejects_empty_run(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="24", with_evaluation=False, with_attendance=False)
    run_id = create_run(client, fx).json()["id"]

    resp = client.post(
        f"/api/v1/incentive-runs/{run_id}/submit-audit",
        headers=auth_headers(client, fx.hr.staff_no),
        json={},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "run_has_no_lines"


# ---- snapshot correctness ----------------------------------------------------


def test_line_snapshot_immune_to_later_rate_edit(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="25", flat_ref_amount=Decimal(1000))
    run = create_run(client, fx).json()
    original_flat_ref = Decimal(run["lines"][0]["flat_ref_amount"])

    # Close the rate that was in effect when the run was created and open a new
    # one later — simulates HR updating the rate card sometime afterward. The
    # run's line was already snapshotted from the old rate and must not move.
    original_rate = db_session.scalars(
        select(PositionRate).where(PositionRate.position_id == fx.position.id)
    ).first()
    original_rate.effective_to = date(2030, 6, 1)
    db_session.add(
        PositionRate(
            position_id=fx.position.id,
            effective_from=date(2030, 6, 1),
            flat_ref_amount=Decimal(9999),
        )
    )
    db_session.commit()

    refetched = client.get(
        f"/api/v1/incentive-runs/{run['id']}", headers=auth_headers(client, fx.hr.staff_no)
    ).json()
    assert Decimal(refetched["lines"][0]["flat_ref_amount"]) == original_flat_ref


# ---- my incentives + history --------------------------------------------------


def test_my_incentives_only_shows_approved_runs(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="26")
    employee_user = make_user(
        db_session, "IEMPUSER26", roles=["employee"], employee_id=fx.employee.id
    )
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)
    employee_headers = auth_headers(client, employee_user.staff_no)
    run_id = create_run(client, fx).json()["id"]

    before = client.get("/api/v1/incentive-runs/my/incentives", headers=employee_headers)
    assert before.json() == []

    client.post(f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/complete-audit", headers=pmo_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/approve", headers=fm_headers, json={})

    after = client.get("/api/v1/incentive-runs/my/incentives", headers=employee_headers)
    assert after.status_code == 200
    assert len(after.json()) == 1
    assert Decimal(after.json()[0]["final_amount"]) == Decimal("720.00")


def test_run_history_records_full_transition_chain(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="27")
    hr_headers = auth_headers(client, fx.hr.staff_no)
    pmo_headers = auth_headers(client, fx.pmo.staff_no)
    fm_headers = auth_headers(client, fx.fm.staff_no)
    run_id = create_run(client, fx).json()["id"]
    client.post(f"/api/v1/incentive-runs/{run_id}/submit-audit", headers=hr_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/complete-audit", headers=pmo_headers, json={})
    client.post(f"/api/v1/incentive-runs/{run_id}/approve", headers=fm_headers, json={})

    history = client.get(f"/api/v1/incentive-runs/{run_id}/history", headers=hr_headers).json()
    assert [h["action"] for h in history] == ["submit_audit", "complete_audit", "approve"]


def test_service_get_history_404_for_missing_run(db_session: Session) -> None:
    from app.common.errors import AppError

    try:
        incentives_service.get_history(db_session, 999999)
        raise AssertionError("expected not_found")
    except AppError as exc:
        assert exc.status_code == 404
