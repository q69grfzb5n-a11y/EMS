from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.common.enums import RoleCode
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.attendance import service
from app.modules.attendance.models import (
    AttendanceImport,
    AttendanceRecord,
    AttendanceZeroFlag,
    IncentivePeriod,
)
from app.modules.attendance.schemas import (
    AttendanceImportOut,
    AttendanceRecordEmployeeBrief,
    AttendanceRecordOut,
    AttendanceZeroFlagOut,
    ImportPreviewOut,
    IncentivePeriodCreateRequest,
    IncentivePeriodOut,
    RowIssueOut,
    ZeroFlagOverrideRequest,
)
from app.modules.auth.models import User

PeriodWriters = Annotated[User, Depends(require_roles(RoleCode.HR, RoleCode.PMO))]
ImportWriters = Annotated[User, Depends(require_roles(RoleCode.HR))]
FlagOverriders = Annotated[User, Depends(require_roles(RoleCode.HR))]

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _period_to_out(period: IncentivePeriod) -> IncentivePeriodOut:
    return IncentivePeriodOut(
        id=period.id,
        year=period.year,
        month=period.month,
        target_pool=period.target_pool,
        actual_pool=period.actual_pool,
        status=period.status,
    )


def _import_to_out(attendance_import: AttendanceImport) -> AttendanceImportOut:
    return AttendanceImportOut(
        id=attendance_import.id,
        period_id=attendance_import.period_id,
        original_filename=attendance_import.original_filename,
        uploaded_by_user_id=attendance_import.uploaded_by_user_id,
        row_count=attendance_import.row_count,
        error_report=attendance_import.error_report,
        status=attendance_import.status,
        created_at=attendance_import.created_at,
    )


def _record_to_out(record: AttendanceRecord) -> AttendanceRecordOut:
    return AttendanceRecordOut(
        id=record.id,
        period_id=record.period_id,
        employee=AttendanceRecordEmployeeBrief(
            id=record.employee.id,
            staff_no=record.employee.staff_no,
            full_name_en=record.employee.full_name_en,
            full_name_ar=record.employee.full_name_ar,
        ),
        present=record.present,
        off_days=record.off_days,
        absent=record.absent,
        leave=record.leave,
        public_holiday=record.public_holiday,
        deduct_min=record.deduct_min,
        over_time=record.over_time,
        approved=record.approved,
        pending_approval=record.pending_approval,
        submitted=record.submitted,
        approved_over_time=record.approved_over_time,
    )


def _flag_to_out(flag: AttendanceZeroFlag) -> AttendanceZeroFlagOut:
    return AttendanceZeroFlagOut(
        id=flag.id,
        employee_id=flag.employee_id,
        period_from_id=flag.period_from_id,
        period_to_id=flag.period_to_id,
        total_leave_absence_days=flag.total_leave_absence_days,
        allowance_days=flag.allowance_days,
        is_overridden=flag.is_overridden,
        override_reason=flag.override_reason,
    )


@router.get("/periods", response_model=list[IncentivePeriodOut])
def list_periods_endpoint(_user: CurrentUser, db: DbSession) -> list[IncentivePeriodOut]:
    return [_period_to_out(p) for p in service.list_periods(db)]


@router.post("/periods", response_model=IncentivePeriodOut, status_code=201)
def create_period_endpoint(
    payload: IncentivePeriodCreateRequest, actor: PeriodWriters, db: DbSession
) -> IncentivePeriodOut:
    period = service.get_or_create_period(db, actor, payload.year, payload.month)
    return _period_to_out(period)


@router.get("/periods/{period_id}", response_model=IncentivePeriodOut)
def get_period_endpoint(period_id: int, _user: CurrentUser, db: DbSession) -> IncentivePeriodOut:
    return _period_to_out(service.get_period(db, period_id))


@router.post("/periods/{period_id}/lock", response_model=IncentivePeriodOut)
def lock_period_endpoint(period_id: int, actor: PeriodWriters, db: DbSession) -> IncentivePeriodOut:
    return _period_to_out(service.set_period_locked(db, actor, period_id, locked=True))


@router.post("/periods/{period_id}/unlock", response_model=IncentivePeriodOut)
def unlock_period_endpoint(
    period_id: int, actor: PeriodWriters, db: DbSession
) -> IncentivePeriodOut:
    return _period_to_out(service.set_period_locked(db, actor, period_id, locked=False))


@router.post("/periods/{period_id}/imports", response_model=ImportPreviewOut | AttendanceImportOut)
async def upload_import_endpoint(
    period_id: int,
    actor: ImportWriters,
    db: DbSession,
    response: Response,
    file: Annotated[UploadFile, File()],
    dry_run: Annotated[bool, Query()] = True,
) -> ImportPreviewOut | AttendanceImportOut:
    content = await file.read()
    if dry_run:
        preview = service.preview_import(db, period_id, content)
        return ImportPreviewOut(
            period_id=preview.period_id,
            total_rows=preview.total_rows,
            matched_count=preview.matched_count,
            unmatched_count=preview.unmatched_count,
            unmatched_staff_nos=preview.unmatched_staff_nos,
            issues=[RowIssueOut(**i) for i in preview.issues],
            has_errors=preview.has_errors,
        )

    attendance_import = service.commit_import(
        db, actor, period_id, filename=file.filename or "upload.xlsx", content=content
    )
    response.status_code = 201
    return _import_to_out(attendance_import)


@router.get("/periods/{period_id}/imports", response_model=list[AttendanceImportOut])
def list_imports_endpoint(
    period_id: int, _user: CurrentUser, db: DbSession
) -> list[AttendanceImportOut]:
    return [_import_to_out(i) for i in service.list_imports(db, period_id)]


@router.get("/imports/{import_id}", response_model=AttendanceImportOut)
def get_import_endpoint(import_id: int, _user: CurrentUser, db: DbSession) -> AttendanceImportOut:
    return _import_to_out(service.get_import(db, import_id))


@router.get("/periods/{period_id}/records", response_model=list[AttendanceRecordOut])
def list_records_endpoint(
    period_id: int, user: CurrentUser, db: DbSession
) -> list[AttendanceRecordOut]:
    return [_record_to_out(r) for r in service.list_records_scoped(db, user, period_id)]


@router.get("/zero-flags", response_model=list[AttendanceZeroFlagOut])
def list_zero_flags_endpoint(
    _user: CurrentUser, db: DbSession, employee_id: int | None = None
) -> list[AttendanceZeroFlagOut]:
    return [_flag_to_out(f) for f in service.list_zero_flags(db, employee_id=employee_id)]


@router.post("/zero-flags/{flag_id}/override", response_model=AttendanceZeroFlagOut)
def override_zero_flag_endpoint(
    flag_id: int, payload: ZeroFlagOverrideRequest, actor: FlagOverriders, db: DbSession
) -> AttendanceZeroFlagOut:
    flag = service.override_zero_flag(db, actor, flag_id, reason=payload.reason)
    return _flag_to_out(flag)
