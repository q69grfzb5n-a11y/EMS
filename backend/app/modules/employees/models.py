from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import EmploymentStatus
from app.db.base import Base, TimestampMixin
from app.modules.org.models import Department, Position


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    __table_args__ = (
        Index(
            "ix_employees_full_name_ar_trgm",
            "full_name_ar",
            postgresql_using="gin",
            postgresql_ops={"full_name_ar": "gin_trgm_ops"},
        ),
        Index(
            "ix_employees_full_name_en_trgm",
            "full_name_en",
            postgresql_using="gin",
            postgresql_ops={"full_name_en": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    staff_no: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name_ar: Mapped[str] = mapped_column(String(200))
    # Backfilled from the attendance export by import_legacy.py — absent for unmatched rows.
    full_name_en: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("departments.id"))
    # ACTUAL position (workbook "Actual Position Final"), not the Oracle title-of-record.
    position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("positions.id"))
    contract_position_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contract_years: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    contract_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employment_status: Mapped[str] = mapped_column(
        String(20), default=EmploymentStatus.ACTIVE.value
    )

    department: Mapped["Department"] = relationship()
    position: Mapped["Position"] = relationship()
    salaries: Mapped[list["EmployeeSalary"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    evaluation_assignment: Mapped["EvaluationAssignment | None"] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )


class EmployeeSalary(Base, TimestampMixin):
    """Temporal, separate restricted table. As-of rule = first day of incentive month."""

    __tablename__ = "employee_salaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    employee: Mapped["Employee"] = relationship(back_populates="salaries")


class EvaluationAssignment(Base, TimestampMixin):
    """One active reviewer per employee — replace-on-reassign, mirrors user_roles."""

    __tablename__ = "evaluation_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id"), unique=True)
    reviewer_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    assigned_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    employee: Mapped["Employee"] = relationship(back_populates="evaluation_assignment")
