from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import IncentiveRunStatus
from app.db.base import Base, TimestampMixin
from app.modules.employees.models import Employee


class IncentiveRun(Base, TimestampMixin):
    """One monthly calculation pass, org-wide. `params` freezes the formula
    mode/rounding config used at creation (survives later config changes);
    `exceptions` freezes the list of employees who did NOT get a line and why
    — both snapshots, same spirit as `incentive_line_items`' full input
    snapshot below. Only one run per period may ever reach `approved`
    (partial unique index)."""

    __tablename__ = "incentive_runs"
    __table_args__ = (
        UniqueConstraint("period_id", "run_no", name="uq_incentive_runs_period_run_no"),
        Index(
            "uq_incentive_runs_one_approved_per_period",
            "period_id",
            unique=True,
            postgresql_where=text("status = 'approved'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incentive_periods.id"), index=True
    )
    run_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=IncentiveRunStatus.DRAFT.value)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    exceptions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    lines: Mapped[list["IncentiveLineItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class IncentiveLineItem(Base, TimestampMixin):
    """Full input snapshot per PLAN §6.1 — every value the engine used is
    stored as a column, not re-derived from live master data, so an approved
    payout is immune to a salary/rate edit made afterward."""

    __tablename__ = "incentive_line_items"
    __table_args__ = (
        UniqueConstraint("run_id", "employee_id", name="uq_incentive_line_items_run_employee"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("incentive_runs.id"), index=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id"), index=True)
    evaluation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("evaluations.id"), nullable=True
    )

    evaluation_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    formula_mode: Mapped[str] = mapped_column(String(20))
    flat_ref_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    base_salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    position_incentive_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    attendance_factor: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"))
    target_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 6))

    computed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    override_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1)

    run: Mapped["IncentiveRun"] = relationship(back_populates="lines")
    employee: Mapped["Employee"] = relationship()
