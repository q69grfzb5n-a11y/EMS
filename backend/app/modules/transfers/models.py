from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import TransferStatus
from app.db.base import Base, TimestampMixin
from app.modules.employees.models import Employee
from app.modules.org.models import Department


class TransferRequest(Base, TimestampMixin):
    """One employee department move, snapshot-from + requested-to, applied at
    `effective_date` (see transfers/service.py). `from_department_id` is pinned
    at creation time, same pattern as evaluations' `template_version_id`."""

    __tablename__ = "transfer_requests"
    __table_args__ = (
        CheckConstraint(
            "from_department_id <> to_department_id",
            name="different_departments",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id"), index=True)
    from_department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("departments.id"))
    to_department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("departments.id"))
    effective_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TransferStatus.DRAFT.value)
    requested_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))

    employee: Mapped["Employee"] = relationship()
    from_department: Mapped["Department"] = relationship(foreign_keys=[from_department_id])
    to_department: Mapped["Department"] = relationship(foreign_keys=[to_department_id])
