import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.common.audit import write_audit
from app.common.enums import AttendanceImportStatus, PeriodStatus
from app.common.errors import bad_request, conflict, not_found
from app.modules.attendance.importer import ParsedAttendanceRow, RowIssue, parse_attendance_file
from app.modules.attendance.models import (
    AttendanceImport,
    AttendanceRecord,
    AttendanceZeroFlag,
    IncentivePeriod,
)
from app.modules.attendance.zero_rule import PeriodAttendance, evaluate_zero_rule
from app.modules.auth.models import User
from app.modules.employees.models import Employee
from app.modules.employees.service import get_employee_by_staff_no, list_employees_scoped


def get_or_create_period(db: Session, actor: User, year: int, month: int) -> IncentivePeriod:
    period = db.scalars(
        select(IncentivePeriod).where(IncentivePeriod.year == year, IncentivePeriod.month == month)
    ).first()
    if period is not None:
        return period

    period = IncentivePeriod(year=year, month=month)
    db.add(period)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_incentive_period",
        entity_type="incentive_period",
        entity_id=period.id,
        after={"year": year, "month": month},
    )
    db.commit()
    return period


def list_periods(db: Session) -> list[IncentivePeriod]:
    stmt = select(IncentivePeriod).order_by(
        IncentivePeriod.year.desc(), IncentivePeriod.month.desc()
    )
    return list(db.scalars(stmt))


def get_period(db: Session, period_id: int) -> IncentivePeriod:
    period = db.get(IncentivePeriod, period_id)
    if period is None:
        raise not_found("Period not found")
    return period


def set_period_locked(db: Session, actor: User, period_id: int, *, locked: bool) -> IncentivePeriod:
    period = get_period(db, period_id)
    period.status = PeriodStatus.LOCKED.value if locked else PeriodStatus.OPEN.value
    write_audit(
        db,
        actor_user_id=actor.id,
        action="lock_period" if locked else "unlock_period",
        entity_type="incentive_period",
        entity_id=period.id,
    )
    db.commit()
    return period


@dataclass
class MatchedRow:
    parsed: ParsedAttendanceRow
    employee_id: int | None


@dataclass
class ImportPreview:
    period_id: int
    total_rows: int
    matched_count: int
    unmatched_count: int
    unmatched_staff_nos: list[str]
    issues: list[dict[str, Any]]
    has_errors: bool


def _issue_to_dict(issue: RowIssue) -> dict[str, Any]:
    return {
        "row_number": issue.row_number,
        "staff_no": issue.staff_no,
        "severity": issue.severity,
        "message": issue.message,
    }


def _parse_and_match(
    db: Session, period: IncentivePeriod, content: bytes
) -> tuple[list[MatchedRow], list[RowIssue], bool]:
    parse_result = parse_attendance_file(
        content, declared_year=period.year, declared_month=period.month
    )
    matched: list[MatchedRow] = []
    for row in parse_result.rows:
        employee = get_employee_by_staff_no(db, row.staff_no)
        matched.append(
            MatchedRow(parsed=row, employee_id=employee.id if employee is not None else None)
        )
    return matched, parse_result.issues, parse_result.has_errors


def preview_import(db: Session, period_id: int, content: bytes) -> ImportPreview:
    period = get_period(db, period_id)
    matched, issues, has_errors = _parse_and_match(db, period, content)
    unmatched = [m.parsed.staff_no for m in matched if m.employee_id is None]
    return ImportPreview(
        period_id=period.id,
        total_rows=len(matched),
        matched_count=len(matched) - len(unmatched),
        unmatched_count=len(unmatched),
        unmatched_staff_nos=unmatched,
        issues=[_issue_to_dict(i) for i in issues],
        has_errors=has_errors,
    )


def commit_import(
    db: Session, actor: User, period_id: int, *, filename: str, content: bytes
) -> AttendanceImport:
    period = get_period(db, period_id)
    if period.status == PeriodStatus.LOCKED.value:
        raise conflict(
            "This period is locked; attendance can no longer be imported", code="period_locked"
        )

    sha256 = hashlib.sha256(content).hexdigest()
    duplicate = db.scalars(
        select(AttendanceImport).where(
            AttendanceImport.period_id == period_id,
            AttendanceImport.file_sha256 == sha256,
            AttendanceImport.status == AttendanceImportStatus.ACTIVE.value,
        )
    ).first()
    if duplicate is not None:
        raise conflict(
            "This exact file has already been imported for this period", code="duplicate_import"
        )

    matched, issues, has_errors = _parse_and_match(db, period, content)
    if has_errors or not matched:
        raise bad_request(
            "The file could not be imported — fix the errors and try again",
            code="import_has_errors",
            details=[_issue_to_dict(i) for i in issues],
        )

    previous_active = db.scalars(
        select(AttendanceImport).where(
            AttendanceImport.period_id == period_id,
            AttendanceImport.status == AttendanceImportStatus.ACTIVE.value,
        )
    ).first()
    if previous_active is not None:
        previous_active.status = AttendanceImportStatus.SUPERSEDED.value
        db.flush()

    unmatched = [m for m in matched if m.employee_id is None]
    matched_rows = [m for m in matched if m.employee_id is not None]
    all_issues = [_issue_to_dict(i) for i in issues]
    for m in unmatched:
        all_issues.append(
            {
                "row_number": m.parsed.row_number,
                "staff_no": m.parsed.staff_no,
                "severity": "warning",
                "message": "No employee found with this staff number",
            }
        )

    attendance_import = AttendanceImport(
        period_id=period_id,
        file_sha256=sha256,
        original_filename=filename,
        uploaded_by_user_id=actor.id,
        row_count=len(matched),
        error_report=all_issues,
    )
    db.add(attendance_import)
    db.flush()

    if matched_rows:
        values = [
            {
                "period_id": period_id,
                "employee_id": m.employee_id,
                "import_id": attendance_import.id,
                "present": m.parsed.present,
                "off_days": m.parsed.off_days,
                "absent": m.parsed.absent,
                "leave": m.parsed.leave,
                "public_holiday": m.parsed.public_holiday,
                "deduct_min": m.parsed.deduct_min,
                "over_time": m.parsed.over_time,
                "approved": m.parsed.approved,
                "pending_approval": m.parsed.pending_approval,
                "submitted": m.parsed.submitted,
                "approved_over_time": m.parsed.approved_over_time,
            }
            for m in matched_rows
        ]
        insert_stmt = pg_insert(AttendanceRecord).values(values)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["period_id", "employee_id"],
            set_={
                "import_id": insert_stmt.excluded.import_id,
                "present": insert_stmt.excluded.present,
                "off_days": insert_stmt.excluded.off_days,
                "absent": insert_stmt.excluded.absent,
                "leave": insert_stmt.excluded.leave,
                "public_holiday": insert_stmt.excluded.public_holiday,
                "deduct_min": insert_stmt.excluded.deduct_min,
                "over_time": insert_stmt.excluded.over_time,
                "approved": insert_stmt.excluded.approved,
                "pending_approval": insert_stmt.excluded.pending_approval,
                "submitted": insert_stmt.excluded.submitted,
                "approved_over_time": insert_stmt.excluded.approved_over_time,
            },
        )
        db.execute(upsert_stmt)

    write_audit(
        db,
        actor_user_id=actor.id,
        action="commit_attendance_import",
        entity_type="attendance_import",
        entity_id=attendance_import.id,
        after={
            "period_id": period_id,
            "row_count": len(matched),
            "matched": len(matched_rows),
            "unmatched": len(unmatched),
        },
    )
    db.commit()

    _recompute_zero_flags(
        db, period, [m.employee_id for m in matched_rows if m.employee_id is not None]
    )
    return attendance_import


def _trailing_period_ids(db: Session, period: IncentivePeriod, *, count: int) -> list[int]:
    """Chronologically ordered ids (oldest first) of the `count` most recent
    existing periods up to and including `period`."""
    stmt = (
        select(IncentivePeriod.id, IncentivePeriod.year, IncentivePeriod.month)
        .where(
            (IncentivePeriod.year < period.year)
            | ((IncentivePeriod.year == period.year) & (IncentivePeriod.month <= period.month))
        )
        .order_by(IncentivePeriod.year.desc(), IncentivePeriod.month.desc())
        .limit(count)
    )
    rows = db.execute(stmt).all()
    ordered = sorted(rows, key=lambda r: (r.year, r.month))
    return [r.id for r in ordered]


def _recompute_zero_flags(db: Session, period: IncentivePeriod, employee_ids: list[int]) -> None:
    if not employee_ids:
        return
    trailing_ids = _trailing_period_ids(db, period, count=6)
    if not trailing_ids:
        return

    for employee_id in employee_ids:
        employee = db.get(Employee, employee_id)
        if employee is None:
            continue
        records = db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.period_id.in_(trailing_ids),
            )
        ).all()
        by_period = {r.period_id: r for r in records}
        trailing_attendance = [
            PeriodAttendance(
                period_id=pid, leave_days=by_period[pid].leave, absent_days=by_period[pid].absent
            )
            for pid in trailing_ids
            if pid in by_period
        ]
        result = evaluate_zero_rule(
            contract_years=employee.contract_years, trailing_periods=trailing_attendance
        )
        if result is None or not result.breached:
            continue

        existing = db.scalars(
            select(AttendanceZeroFlag).where(
                AttendanceZeroFlag.employee_id == employee_id,
                AttendanceZeroFlag.period_from_id == result.period_from_id,
                AttendanceZeroFlag.period_to_id == result.period_to_id,
            )
        ).first()
        if existing is not None:
            continue

        db.add(
            AttendanceZeroFlag(
                employee_id=employee_id,
                period_from_id=result.period_from_id,
                period_to_id=result.period_to_id,
                total_leave_absence_days=result.total_leave_absence_days,
                allowance_days=result.allowance_days,
            )
        )
    db.commit()


def list_imports(db: Session, period_id: int) -> list[AttendanceImport]:
    get_period(db, period_id)  # 404 if missing
    stmt = (
        select(AttendanceImport)
        .where(AttendanceImport.period_id == period_id)
        .order_by(AttendanceImport.created_at.desc())
    )
    return list(db.scalars(stmt))


def get_import(db: Session, import_id: int) -> AttendanceImport:
    attendance_import = db.get(AttendanceImport, import_id)
    if attendance_import is None:
        raise not_found("Attendance import not found")
    return attendance_import


def list_records_scoped(db: Session, actor: User, period_id: int) -> list[AttendanceRecord]:
    get_period(db, period_id)  # 404 if missing
    allowed_employee_ids = {e.id for e in list_employees_scoped(db, actor)}
    if not allowed_employee_ids:
        return []
    stmt = (
        select(AttendanceRecord)
        .where(
            AttendanceRecord.period_id == period_id,
            AttendanceRecord.employee_id.in_(allowed_employee_ids),
        )
        .options(selectinload(AttendanceRecord.employee))
    )
    return list(db.scalars(stmt))


def list_zero_flags(db: Session, *, employee_id: int | None = None) -> list[AttendanceZeroFlag]:
    stmt = select(AttendanceZeroFlag).order_by(AttendanceZeroFlag.id.desc())
    if employee_id is not None:
        stmt = stmt.where(AttendanceZeroFlag.employee_id == employee_id)
    return list(db.scalars(stmt))


def override_zero_flag(
    db: Session, actor: User, flag_id: int, *, reason: str
) -> AttendanceZeroFlag:
    flag = db.get(AttendanceZeroFlag, flag_id)
    if flag is None:
        raise not_found("Zero flag not found")

    flag.is_overridden = True
    flag.override_reason = reason
    flag.overridden_by_user_id = actor.id
    write_audit(
        db,
        actor_user_id=actor.id,
        action="override_zero_flag",
        entity_type="attendance_zero_flag",
        entity_id=flag.id,
        after={"reason": reason},
    )
    db.commit()
    return flag
