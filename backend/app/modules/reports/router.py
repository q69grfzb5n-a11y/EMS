import io
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.common.enums import RoleCode
from app.core.deps import DbSession, require_roles
from app.modules.attendance.service import get_period
from app.modules.auth.models import User
from app.modules.incentives.export import build_finance_workbook
from app.modules.kpi_templates.service import get_version
from app.modules.reports import service
from app.modules.reports.blank_template import build_blank_evaluation_workbook
from app.modules.reports.pdf import render_pdf
from app.modules.reports.schemas import PeriodSummaryOut

FinanceReaders = Annotated[
    User,
    Depends(
        require_roles(
            RoleCode.HR, RoleCode.PMO, RoleCode.ADMIN, RoleCode.FACTORY_MANAGER, RoleCode.FINANCE
        )
    ),
]
TemplateDownloaders = Annotated[
    User,
    Depends(
        require_roles(
            RoleCode.HR,
            RoleCode.PMO,
            RoleCode.ADMIN,
            RoleCode.FACTORY_MANAGER,
            RoleCode.DEPT_MANAGER,
            RoleCode.REVIEWER,
        )
    ),
]

router = APIRouter(prefix="/reports", tags=["reports"])

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _attachment_response(content: bytes, *, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/periods/{period_id}/summary", response_model=PeriodSummaryOut)
def period_summary_endpoint(
    period_id: int, _actor: FinanceReaders, db: DbSession
) -> PeriodSummaryOut:
    return service.get_period_summary(db, period_id)


@router.get("/runs/{run_id}/finance-excel")
def finance_excel_endpoint(run_id: int, _actor: FinanceReaders, db: DbSession) -> Response:
    run = service.require_approved_run(db, run_id)
    rows = service.build_payout_rows(run)
    period = get_period(db, run.period_id)
    workbook = build_finance_workbook(
        run_no=run.run_no, year=period.year, month=period.month, rows=rows
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    filename = f"incentive_payout_run_{run.run_no}.xlsx"
    return _attachment_response(buffer.getvalue(), media_type=_XLSX_MEDIA_TYPE, filename=filename)


@router.get("/runs/{run_id}/finance-pdf")
def finance_pdf_endpoint(run_id: int, _actor: FinanceReaders, db: DbSession) -> Response:
    run = service.require_approved_run(db, run_id)
    context = service.build_finance_pdf_context(db, run)
    pdf_bytes = render_pdf("finance_summary.html", context)
    filename = f"incentive_summary_run_{run.run_no}.pdf"
    return _attachment_response(pdf_bytes, media_type="application/pdf", filename=filename)


@router.get("/kpi-templates/{version_id}/blank-excel")
def blank_excel_endpoint(version_id: int, actor: TemplateDownloaders, db: DbSession) -> Response:
    version = get_version(db, version_id)
    roster = service.list_roster_for_template(db, actor, version.template_id, as_of=date.today())
    workbook = build_blank_evaluation_workbook(
        template_name_en=version.template.name_en,
        criteria=service.build_criteria_specs(version),
        roster=service.build_roster_members(roster),
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    filename = f"blank_evaluation_{version.template.code}_v{version.version_no}.xlsx"
    return _attachment_response(buffer.getvalue(), media_type=_XLSX_MEDIA_TYPE, filename=filename)


@router.get("/kpi-templates/{version_id}/blank-pdf")
def blank_pdf_endpoint(version_id: int, actor: TemplateDownloaders, db: DbSession) -> Response:
    version = get_version(db, version_id)
    roster = service.list_roster_for_template(db, actor, version.template_id, as_of=date.today())
    context = {
        "template_name_ar": version.template.name_ar,
        "criteria": [
            {"name_ar": c.name_ar, "max_marks": c.max_marks} for c in version.criteria
        ],
        "roster": [
            {"staff_no": e.staff_no, "full_name_ar": e.full_name_ar} for e in roster
        ]
        or [{"staff_no": "", "full_name_ar": ""}],
    }
    pdf_bytes = render_pdf("blank_evaluation.html", context)
    filename = f"blank_evaluation_{version.template.code}_v{version.version_no}.pdf"
    return _attachment_response(pdf_bytes, media_type="application/pdf", filename=filename)
