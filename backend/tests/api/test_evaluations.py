from dataclasses import dataclass
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.attendance.models import AttendanceRecord, IncentivePeriod
from app.modules.auth.models import Role, User, UserRole
from app.modules.employees.models import Employee, EvaluationAssignment
from app.modules.evaluations import service
from app.modules.kpi_templates.models import (
    KpiCriterion,
    KpiTemplate,
    KpiTemplateAssignment,
    KpiTemplateVersion,
)
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


@dataclass
class Fixture:
    dept: Department
    position: Position
    template: KpiTemplate
    version_id: int
    criteria: list[KpiCriterion]
    employee: Employee
    period: IncentivePeriod
    reviewer: User
    dept_manager: User
    hr: User


def build_fixture(
    db_session: Session, *, suffix: str, contract_years: int | None = None
) -> Fixture:
    dept = Department(code=f"D{suffix}", name_en=f"Dept {suffix}", name_ar="قسم")
    position = Position(code=f"pos{suffix}", title_en=f"Pos {suffix}", title_ar="وظيفة")
    db_session.add_all([dept, position])
    db_session.flush()

    template = KpiTemplate(code=f"TPL{suffix}", name_en="Template", name_ar="نموذج")
    db_session.add(template)
    db_session.flush()
    version = KpiTemplateVersion(template_id=template.id, version_no=1, status="active")
    db_session.add(version)
    db_session.flush()
    c1 = KpiCriterion(
        template_version_id=version.id,
        name_en="Quality",
        name_ar="جودة",
        max_marks=70,
        sort_order=1,
    )
    c2 = KpiCriterion(
        template_version_id=version.id,
        name_en="Attendance",
        name_ar="حضور",
        max_marks=30,
        sort_order=2,
        auto_source="absence_penalty",
        auto_params={"penalty_per_absence": 5},
        allow_negative=True,
    )
    db_session.add_all([c1, c2])
    db_session.flush()

    db_session.add(
        KpiTemplateAssignment(
            position_id=position.id, template_id=template.id, effective_from=date(2020, 1, 1)
        )
    )

    employee = Employee(
        staff_no=f"EMP{suffix}",
        full_name_ar="اسم الموظف",
        department_id=dept.id,
        position_id=position.id,
        contract_years=contract_years,
    )
    db_session.add(employee)
    db_session.flush()

    # Periods are global per calendar month (not per-department), so two
    # fixtures built in the same test correctly share one period — mirrors
    # get_or_create_period in the real service layer.
    period = db_session.scalars(
        select(IncentivePeriod).where(IncentivePeriod.year == 2026, IncentivePeriod.month == 6)
    ).first()
    if period is None:
        period = IncentivePeriod(year=2026, month=6)
        db_session.add(period)
        db_session.flush()

    reviewer = make_user(db_session, f"R{suffix}", roles=["reviewer"])
    db_session.add(EvaluationAssignment(employee_id=employee.id, reviewer_user_id=reviewer.id))

    manager_employee = Employee(
        staff_no=f"MGR{suffix}", full_name_ar="مدير", department_id=dept.id, position_id=position.id
    )
    db_session.add(manager_employee)
    db_session.flush()
    dept_manager = make_user(
        db_session, f"M{suffix}", roles=["dept_manager"], employee_id=manager_employee.id
    )
    hr = make_user(db_session, f"HR{suffix}", roles=["hr"])

    db_session.commit()
    return Fixture(
        dept=dept,
        position=position,
        template=template,
        version_id=version.id,
        criteria=[c1, c2],
        employee=employee,
        period=period,
        reviewer=reviewer,
        dept_manager=dept_manager,
        hr=hr,
    )


def create_evaluation(
    client: TestClient, fx: "Fixture", *, kind: str = "regular", employee_id: int | None = None
):
    return client.post(
        "/api/v1/evaluations",
        headers=auth_headers(client, fx.hr.staff_no),
        json={
            "employee_id": employee_id if employee_id is not None else fx.employee.id,
            "period_id": fx.period.id,
            "kind": kind,
        },
    )


# ---- creation ----------------------------------------------------------


def test_create_evaluation_pins_active_template_version(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="1")

    resp = create_evaluation(client, fx)

    assert resp.status_code == 201
    body = resp.json()
    assert body["template_version_id"] == fx.version_id
    assert body["status"] == "draft"
    assert body["owner_user_id"] == fx.reviewer.id
    assert len(body["scores"]) == 2


def test_create_evaluation_prefills_absence_suggestion_from_real_attendance(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="2")
    db_session.add(
        AttendanceRecord(
            period_id=fx.period.id,
            employee_id=fx.employee.id,
            import_id=_fake_import(db_session, fx.period.id),
            present=25,
            off_days=2,
            absent=3,
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

    resp = create_evaluation(client, fx)

    assert resp.status_code == 201
    attendance_score = next(s for s in resp.json()["scores"] if s["name_en"] == "Attendance")
    # max_marks 30 - 5*3 absences = 15
    assert attendance_score["auto_suggested_marks"] == "15.00"
    assert attendance_score["awarded_marks"] == "15.00"


def _fake_import(db_session: Session, period_id: int) -> int:
    from app.modules.attendance.models import AttendanceImport

    user = db_session.scalars(select(User)).first()
    imp = AttendanceImport(
        period_id=period_id,
        file_sha256="0" * 64,
        original_filename="x.xlsx",
        uploaded_by_user_id=user.id if user else 1,
        row_count=1,
        status="active",
    )
    db_session.add(imp)
    db_session.flush()
    return imp.id


def test_create_evaluation_conflict_when_already_exists(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="3")

    first = create_evaluation(client, fx)
    assert first.status_code == 201
    second = create_evaluation(client, fx)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_exists"


def test_create_evaluation_bad_request_when_no_template_assigned(
    client: TestClient, db_session: Session
) -> None:
    dept = Department(code="DNONE", name_en="D", name_ar="د")
    position = Position(code="posnone", title_en="P", title_ar="و")
    db_session.add_all([dept, position])
    db_session.flush()
    employee = Employee(
        staff_no="ENONE", full_name_ar="اسم", department_id=dept.id, position_id=position.id
    )
    db_session.add(employee)
    db_session.flush()
    period = IncentivePeriod(year=2026, month=7)
    db_session.add(period)
    db_session.commit()
    make_user(db_session, "HRX", roles=["hr"])
    headers = auth_headers(client, "HRX")

    resp = client.post(
        "/api/v1/evaluations",
        headers=headers,
        json={"employee_id": employee.id, "period_id": period.id, "kind": "regular"},
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "no_template_assigned"


def test_template_pinning_survives_later_template_edits(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="4")
    headers = auth_headers(client, fx.reviewer.staff_no)

    create_resp = create_evaluation(client, fx)
    evaluation_id = create_resp.json()["id"]
    original_total = sum(s["max_marks"] for s in create_resp.json()["scores"])

    # Clone the template to v2 and change a weight, then activate it — v1
    # (pinned on the evaluation) must stay exactly as it was.
    make_user(db_session, "PMOX4", roles=["pmo"])
    pmo_headers = auth_headers(client, "PMOX4")
    clone = client.post(
        f"/api/v1/kpi-templates/{fx.template.id}/versions", headers=pmo_headers, json={}
    )
    v2 = clone.json()
    quality_criterion = next(c for c in v2["criteria"] if c["name_en"] == "Quality")
    client.patch(
        f"/api/v1/kpi-templates/criteria/{quality_criterion['id']}",
        headers=pmo_headers,
        json={"max_marks": 40},
    )
    attendance_criterion = next(c for c in v2["criteria"] if c["name_en"] == "Attendance")
    client.patch(
        f"/api/v1/kpi-templates/criteria/{attendance_criterion['id']}",
        headers=pmo_headers,
        json={"max_marks": 60},
    )
    activate = client.post(
        f"/api/v1/kpi-templates/versions/{v2['id']}/activate", headers=pmo_headers
    )
    assert activate.status_code == 200

    reread = client.get(f"/api/v1/evaluations/{evaluation_id}", headers=headers)
    assert reread.status_code == 200
    body = reread.json()
    assert body["template_version_id"] == fx.version_id
    assert sum(s["max_marks"] for s in body["scores"]) == original_total


# ---- update / optimistic lock ------------------------------------------


def test_update_scores_recomputes_score_pct_and_grade(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="5")
    headers = auth_headers(client, fx.reviewer.staff_no)
    created = create_evaluation(client, fx).json()

    resp = client.patch(
        f"/api/v1/evaluations/{created['id']}",
        headers=headers,
        json={
            "row_version": created["row_version"],
            "scores": [
                {"criterion_id": fx.criteria[0].id, "raw_input": 70},
                {"criterion_id": fx.criteria[1].id, "raw_input": 30},
            ],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["score_pct"] == "1.0000"
    assert body["grade"] == "A"
    assert body["row_version"] == created["row_version"] + 1


def test_update_scores_row_version_conflict(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="6")
    headers = auth_headers(client, fx.reviewer.staff_no)
    created = create_evaluation(client, fx).json()

    resp = client.patch(
        f"/api/v1/evaluations/{created['id']}",
        headers=headers,
        json={"row_version": created["row_version"] + 99, "scores": []},
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "row_version_conflict"


def test_update_scores_forbidden_for_non_owner(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="7")
    created = create_evaluation(client, fx).json()

    make_user(db_session, "OTHER7", roles=["reviewer"])
    other_headers = auth_headers(client, "OTHER7")
    resp = client.patch(
        f"/api/v1/evaluations/{created['id']}",
        headers=other_headers,
        json={"row_version": created["row_version"], "scores": []},
    )
    assert resp.status_code == 403


def test_update_scores_rejected_once_submitted(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="8")
    headers = auth_headers(client, fx.reviewer.staff_no)
    created = create_evaluation(client, fx).json()
    client.post(f"/api/v1/evaluations/{created['id']}/submit", headers=headers, json={})

    resp = client.patch(
        f"/api/v1/evaluations/{created['id']}",
        headers=headers,
        json={"row_version": created["row_version"], "scores": []},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "evaluation_not_editable"


# ---- REGULAR transition matrix -----------------------------------------


def test_regular_submit_forbidden_for_non_owner_reviewer(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="9")
    created = create_evaluation(client, fx).json()

    make_user(db_session, "OTHERREV9", roles=["reviewer"])
    other_headers = auth_headers(client, "OTHERREV9")
    resp = client.post(
        f"/api/v1/evaluations/{created['id']}/submit", headers=other_headers, json={}
    )
    assert resp.status_code == 403


def test_regular_invalid_action_from_draft_is_400(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="10")
    headers = auth_headers(client, fx.reviewer.staff_no)
    created = create_evaluation(client, fx).json()

    resp = client.post(f"/api/v1/evaluations/{created['id']}/approve", headers=headers, json={})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_transition"


def test_regular_approve_forbidden_for_dept_manager_of_different_department(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="11")
    other_fx = build_fixture(db_session, suffix="11b")
    headers = auth_headers(client, fx.reviewer.staff_no)
    created = create_evaluation(client, fx).json()
    client.post(f"/api/v1/evaluations/{created['id']}/submit", headers=headers, json={})

    other_dept_headers = auth_headers(client, other_fx.dept_manager.staff_no)
    resp = client.post(
        f"/api/v1/evaluations/{created['id']}/approve", headers=other_dept_headers, json={}
    )
    assert resp.status_code == 403


def test_regular_full_workflow_score_return_fix_approve_with_timeline(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="12")
    reviewer_headers = auth_headers(client, fx.reviewer.staff_no)
    manager_headers = auth_headers(client, fx.dept_manager.staff_no)

    created = create_evaluation(client, fx).json()
    evaluation_id = created["id"]

    scored = client.patch(
        f"/api/v1/evaluations/{evaluation_id}",
        headers=reviewer_headers,
        json={
            "row_version": created["row_version"],
            "scores": [
                {"criterion_id": fx.criteria[0].id, "raw_input": 60},
                {"criterion_id": fx.criteria[1].id, "raw_input": 20},
            ],
        },
    ).json()
    assert scored["score_pct"] == "0.8000"  # (60+20)/100

    submitted = client.post(
        f"/api/v1/evaluations/{evaluation_id}/submit", headers=reviewer_headers, json={}
    ).json()
    assert submitted["status"] == "submitted"

    returned = client.post(
        f"/api/v1/evaluations/{evaluation_id}/return",
        headers=manager_headers,
        json={"comment": "please recheck quality score"},
    ).json()
    assert returned["status"] == "returned"

    fixed = client.patch(
        f"/api/v1/evaluations/{evaluation_id}",
        headers=reviewer_headers,
        json={
            "row_version": returned["row_version"],
            "scores": [
                {"criterion_id": fx.criteria[0].id, "raw_input": 70},
                {"criterion_id": fx.criteria[1].id, "raw_input": 20},
            ],
        },
    ).json()
    assert fixed["score_pct"] == "0.9000"  # (70+20)/100

    resubmitted = client.post(
        f"/api/v1/evaluations/{evaluation_id}/submit", headers=reviewer_headers, json={}
    ).json()
    assert resubmitted["status"] == "submitted"

    approved = client.post(
        f"/api/v1/evaluations/{evaluation_id}/approve", headers=manager_headers, json={}
    ).json()
    assert approved["status"] == "manager_approved"

    history = client.get(
        f"/api/v1/approvals/evaluation/{evaluation_id}/history", headers=manager_headers
    ).json()
    assert [h["action"] for h in history] == ["submit", "return", "submit", "approve"]
    assert history[1]["comment"] == "please recheck quality score"
    assert history[0]["actor_role"] == "reviewer"
    assert history[1]["actor_role"] == "dept_manager"


# ---- SELF_APPRAISAL transition matrix ----------------------------------


def test_self_appraisal_full_workflow(client: TestClient, db_session: Session) -> None:
    fx = build_fixture(db_session, suffix="13")
    key_person = make_user(db_session, "KP13", roles=["key_person"], employee_id=fx.employee.id)
    kp_headers = auth_headers(client, "KP13")
    make_user(db_session, "PMO13", roles=["pmo"])
    pmo_headers = auth_headers(client, "PMO13")
    make_user(db_session, "FM13", roles=["factory_manager"])
    fm_headers = auth_headers(client, "FM13")

    created = create_evaluation(client, fx, kind="self_appraisal")
    assert created.status_code == 201
    evaluation_id = created.json()["id"]
    assert created.json()["owner_user_id"] == key_person.id

    submit = client.post(f"/api/v1/evaluations/{evaluation_id}/submit", headers=kp_headers, json={})
    assert submit.status_code == 200
    assert submit.json()["status"] == "submitted"

    returned = client.post(
        f"/api/v1/evaluations/{evaluation_id}/return",
        headers=pmo_headers,
        json={"comment": "add detail"},
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "returned"

    resubmit = client.post(
        f"/api/v1/evaluations/{evaluation_id}/submit", headers=kp_headers, json={}
    )
    assert resubmit.status_code == 200

    reviewed = client.post(
        f"/api/v1/evaluations/{evaluation_id}/review", headers=pmo_headers, json={}
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "pmo_reviewed"

    fm_forbidden_early = client.post(
        f"/api/v1/evaluations/{evaluation_id}/approve", headers=kp_headers, json={}
    )
    assert fm_forbidden_early.status_code == 403

    approved = client.post(
        f"/api/v1/evaluations/{evaluation_id}/approve", headers=fm_headers, json={}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "fm_approved"


def test_self_appraisal_pmo_cannot_be_bypassed_by_reviewer_role(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="14")
    make_user(db_session, "KP14", roles=["key_person"], employee_id=fx.employee.id)
    kp_headers = auth_headers(client, "KP14")

    created = create_evaluation(client, fx, kind="self_appraisal").json()
    client.post(f"/api/v1/evaluations/{created['id']}/submit", headers=kp_headers, json={})

    # the assigned reviewer for the REGULAR track has no say over a self_appraisal
    resp = client.post(
        f"/api/v1/evaluations/{created['id']}/review",
        headers=auth_headers(client, fx.reviewer.staff_no),
        json={},
    )
    assert resp.status_code == 403


# ---- bulk create ---------------------------------------------------------


def test_bulk_create_skips_employees_without_a_reviewer_and_reports_why(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="15")
    # a second employee in the same dept/position with NO reviewer assignment
    unassigned = Employee(
        staff_no="UNASSIGNED15",
        full_name_ar="بدون مقيم",
        department_id=fx.dept.id,
        position_id=fx.position.id,
    )
    db_session.add(unassigned)
    db_session.commit()

    headers = auth_headers(client, fx.hr.staff_no)

    resp = client.post(
        "/api/v1/evaluations/bulk",
        headers=headers,
        json={"department_id": fx.dept.id, "period_id": fx.period.id, "kind": "regular"},
    )

    assert resp.status_code == 201
    body = resp.json()
    created_employee_ids = {c["employee"]["id"] for c in body["created"]}
    assert fx.employee.id in created_employee_ids
    skipped_ids = {s["employee_id"]: s["reason"] for s in body["skipped"]}
    assert skipped_ids[unassigned.id] == "no_owner_resolved"


# ---- scope enforcement ---------------------------------------------------


def test_list_evaluations_scoped_to_own_department_for_dept_manager(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="16")
    other_fx = build_fixture(db_session, suffix="16b")
    create_evaluation(client, fx)
    create_evaluation(client, other_fx)

    manager_headers = auth_headers(client, fx.dept_manager.staff_no)
    resp = client.get("/api/v1/evaluations", headers=manager_headers)

    assert resp.status_code == 200
    employee_ids = {e["employee"]["id"] for e in resp.json()}
    assert employee_ids == {fx.employee.id}


def test_get_evaluation_forbidden_for_unrelated_reviewer(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="17")
    created = create_evaluation(client, fx).json()

    make_user(db_session, "UNRELATED17", roles=["reviewer"])
    unrelated_headers = auth_headers(client, "UNRELATED17")
    resp = client.get(f"/api/v1/evaluations/{created['id']}", headers=unrelated_headers)
    assert resp.status_code == 403


def test_pending_inbox_shows_reviewer_drafts_and_manager_submitted(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="18")
    reviewer_headers = auth_headers(client, fx.reviewer.staff_no)
    created = create_evaluation(client, fx).json()

    reviewer_inbox = client.get("/api/v1/approvals/pending", headers=reviewer_headers).json()
    assert any(e["id"] == created["id"] for e in reviewer_inbox)

    manager_headers = auth_headers(client, fx.dept_manager.staff_no)
    manager_inbox_before = client.get("/api/v1/approvals/pending", headers=manager_headers).json()
    assert not any(e["id"] == created["id"] for e in manager_inbox_before)

    client.post(f"/api/v1/evaluations/{created['id']}/submit", headers=reviewer_headers, json={})

    manager_inbox_after = client.get("/api/v1/approvals/pending", headers=manager_headers).json()
    assert any(e["id"] == created["id"] for e in manager_inbox_after)
    reviewer_inbox_after = client.get("/api/v1/approvals/pending", headers=reviewer_headers).json()
    assert not any(e["id"] == created["id"] for e in reviewer_inbox_after)


def test_evaluation_create_requires_hr_pmo_or_admin(
    client: TestClient, db_session: Session
) -> None:
    fx = build_fixture(db_session, suffix="19")
    reviewer_headers = auth_headers(client, fx.reviewer.staff_no)

    resp = client.post(
        "/api/v1/evaluations",
        headers=reviewer_headers,
        json={"employee_id": fx.employee.id, "period_id": fx.period.id, "kind": "regular"},
    )
    assert resp.status_code == 403


def test_service_get_history_matches_router(db_session: Session) -> None:
    # sanity: service.get_history 404s for a nonexistent evaluation id
    from app.common.errors import AppError

    try:
        service.get_history(db_session, 999999)
        raise AssertionError("expected not_found")
    except AppError as exc:
        assert exc.status_code == 404
