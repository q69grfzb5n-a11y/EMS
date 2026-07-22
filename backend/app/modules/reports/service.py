from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import EmploymentStatus, IncentiveRunStatus
from app.common.errors import bad_request
from app.modules.attendance.service import get_period
from app.modules.employees.models import Employee
from app.modules.incentives import service as incentives_service
from app.modules.incentives.export import PayoutRow
from app.modules.incentives.models import IncentiveRun
from app.modules.kpi_templates.models import KpiTemplateAssignment, KpiTemplateVersion
from app.modules.reports.blank_template import CriterionSpec, RosterMember
from app.modules.reports.schemas import DeptSummaryOut, PeriodSummaryOut


@dataclass
class DeptTotal:
    department_id: int
    code: str
    name_en: str
    name_ar: str
    employee_count: int = 0
    total_amount: Decimal = field(default_factory=lambda: Decimal(0))


def _dept_totals(run: IncentiveRun) -> list[DeptTotal]:
    by_dept: dict[int, DeptTotal] = {}
    for line in run.lines:
        if line.is_excluded:
            continue
        dept = line.employee.department
        totals = by_dept.setdefault(
            dept.id,
            DeptTotal(
                department_id=dept.id, code=dept.code, name_en=dept.name_en, name_ar=dept.name_ar
            ),
        )
        totals.employee_count += 1
        totals.total_amount += line.final_amount
    return sorted(by_dept.values(), key=lambda d: d.code)


def get_period_summary(db: Session, period_id: int) -> PeriodSummaryOut:
    period = get_period(db, period_id)
    run = incentives_service.get_approved_run_for_period(db, period_id)
    if run is None:
        return PeriodSummaryOut(
            period_id=period.id,
            year=period.year,
            month=period.month,
            run_id=None,
            run_status=None,
            departments=[],
            grand_total=Decimal(0),
        )

    totals = _dept_totals(run)
    return PeriodSummaryOut(
        period_id=period.id,
        year=period.year,
        month=period.month,
        run_id=run.id,
        run_status=run.status,
        departments=[
            DeptSummaryOut(
                department_id=t.department_id,
                code=t.code,
                name_en=t.name_en,
                name_ar=t.name_ar,
                employee_count=t.employee_count,
                total_amount=t.total_amount,
            )
            for t in totals
        ],
        grand_total=sum((t.total_amount for t in totals), Decimal(0)),
    )


def require_approved_run(db: Session, run_id: int) -> IncentiveRun:
    run = incentives_service.get_run(db, run_id)
    if run.status != IncentiveRunStatus.APPROVED.value:
        raise bad_request("Only an approved run can be exported", code="run_not_approved")
    return run


def build_payout_rows(run: IncentiveRun) -> list[PayoutRow]:
    rows = []
    for line in run.lines:
        if line.is_excluded:
            continue
        employee = line.employee
        department = employee.department
        rows.append(
            PayoutRow(
                department_code=department.code,
                department_name_en=department.name_en,
                department_name_ar=department.name_ar,
                staff_no=employee.staff_no,
                full_name_en=employee.full_name_en,
                full_name_ar=employee.full_name_ar,
                evaluation_pct=line.evaluation_pct,
                final_amount=line.final_amount,
            )
        )
    return rows


def build_finance_pdf_context(db: Session, run: IncentiveRun) -> dict[str, object]:
    period = get_period(db, run.period_id)
    totals = _dept_totals(run)
    return {
        "run_no": run.run_no,
        "month_str": f"{period.month:02d}/{period.year}",
        "departments": [
            {
                "name_ar": t.name_ar,
                "employee_count": t.employee_count,
                "total_amount": t.total_amount,
            }
            for t in totals
        ],
        "grand_total": sum((t.total_amount for t in totals), Decimal(0)),
        "total_count": sum(t.employee_count for t in totals),
    }


def list_roster_for_template(db: Session, template_id: int, *, as_of: date) -> list[Employee]:
    position_ids = [
        a.position_id
        for a in db.scalars(
            select(KpiTemplateAssignment).where(
                KpiTemplateAssignment.template_id == template_id,
                KpiTemplateAssignment.effective_from <= as_of,
                (KpiTemplateAssignment.effective_to.is_(None))
                | (KpiTemplateAssignment.effective_to > as_of),
            )
        )
    ]
    if not position_ids:
        return []
    stmt = (
        select(Employee)
        .where(
            Employee.position_id.in_(position_ids),
            Employee.employment_status == EmploymentStatus.ACTIVE.value,
        )
        .order_by(Employee.staff_no)
    )
    return list(db.scalars(stmt))


def build_criteria_specs(version: KpiTemplateVersion) -> list[CriterionSpec]:
    return [
        CriterionSpec(
            name_en=c.name_en, name_ar=c.name_ar, max_marks=c.max_marks, input_mode=c.input_mode
        )
        for c in version.criteria
    ]


def build_roster_members(employees: list[Employee]) -> list[RosterMember]:
    return [
        RosterMember(staff_no=e.staff_no, full_name_en=e.full_name_en, full_name_ar=e.full_name_ar)
        for e in employees
    ]
