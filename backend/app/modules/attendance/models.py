from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import AttendanceImportStatus, PeriodStatus
from app.db.base import Base, TimestampMixin
from app.modules.employees.models import Employee


class IncentivePeriod(Base, TimestampMixin):
    __tablename__ = "incentive_periods"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_incentive_periods_year_month"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger)
    month: Mapped[int] = mapped_column(SmallInteger)
    target_pool: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_pool: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=PeriodStatus.OPEN.value)


class AttendanceImport(Base, TimestampMixin):
    """One row per committed upload. sha256 is unique per period — an identical
    re-upload for the same period is a 409, not a new import (idempotency).
    Never created for dry-run parses."""

    __tablename__ = "attendance_imports"
    __table_args__ = (
        UniqueConstraint("period_id", "file_sha256", name="uq_attendance_imports_period_sha256"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incentive_periods.id"), index=True
    )
    file_sha256: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str] = mapped_column(String(255))
    uploaded_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    row_count: Mapped[int] = mapped_column(SmallInteger)
    error_report: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=AttendanceImportStatus.ACTIVE.value)

    period: Mapped["IncentivePeriod"] = relationship()


class AttendanceRecord(Base, TimestampMixin):
    """One current row per employee+period (upsert ON CONFLICT). All day-count
    columns (present/off_days/absent/leave/public_holiday) come straight from the
    17-column Oracle export; deduct_min/over_time/approved_over_time are the only
    fractional columns (minutes and hours respectively) — everything else in the
    export is a whole-day count, verified against the real file."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("period_id", "employee_id", name="uq_attendance_records_period_employee"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incentive_periods.id"), index=True
    )
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id"), index=True)
    import_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("attendance_imports.id"))

    present: Mapped[int] = mapped_column(SmallInteger)
    off_days: Mapped[int] = mapped_column(SmallInteger)
    absent: Mapped[int] = mapped_column(SmallInteger)
    leave: Mapped[int] = mapped_column(SmallInteger)
    public_holiday: Mapped[int] = mapped_column(SmallInteger)
    deduct_min: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    over_time: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    approved: Mapped[int] = mapped_column(SmallInteger)
    pending_approval: Mapped[int] = mapped_column(SmallInteger)
    submitted: Mapped[int] = mapped_column(SmallInteger)
    approved_over_time: Mapped[Decimal] = mapped_column(Numeric(8, 2))

    period: Mapped["IncentivePeriod"] = relationship()
    employee: Mapped["Employee"] = relationship()
    attendance_import: Mapped["AttendanceImport"] = relationship()


class AttendanceZeroFlag(Base, TimestampMixin):
    """Materialized breach of the rolling leave+absence allowance (45d for a
    1-year contract, 90d for a 2-year contract) over a trailing <=6-period
    window [period_from, period_to]. HR-overridable with a reason; never
    deleted (append-only, matches the no-hard-deletes convention)."""

    __tablename__ = "attendance_zero_flags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id"), index=True)
    period_from_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("incentive_periods.id"))
    period_to_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("incentive_periods.id"))
    total_leave_absence_days: Mapped[int] = mapped_column(SmallInteger)
    allowance_days: Mapped[int] = mapped_column(SmallInteger)
    is_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    employee: Mapped["Employee"] = relationship()
    period_from: Mapped["IncentivePeriod"] = relationship(foreign_keys=[period_from_id])
    period_to: Mapped["IncentivePeriod"] = relationship(foreign_keys=[period_to_id])
