from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Position(Base, TimestampMixin):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title_en: Mapped[str] = mapped_column(String(100))
    title_ar: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    rates: Mapped[list["PositionRate"]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )


class PositionRate(Base, TimestampMixin):
    """Temporal: one non-overlapping window per position (GiST EXCLUDE, see migration)."""

    __tablename__ = "position_rates"
    __table_args__ = (
        CheckConstraint(
            "incentive_pct IS NOT NULL OR flat_ref_amount IS NOT NULL",
            name="ck_position_rates_rate_present",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("positions.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Dual-mode: %-of-salary once HR loads salaries, or the legacy flat SAR reference amount.
    incentive_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    flat_ref_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    position: Mapped["Position"] = relationship(back_populates="rates")
