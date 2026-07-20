from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import EvaluationStatus
from app.db.base import Base, TimestampMixin
from app.modules.employees.models import Employee
from app.modules.kpi_templates.models import KpiCriterion, KpiTemplateVersion


class Evaluation(Base, TimestampMixin):
    """One table, two `kind`s sharing one status column but two distinct
    transition tables (see evaluations/workflow.py) — `kind` never changes
    after creation, so there's no ambiguity about which table governs a row.
    `template_version_id` is pinned at creation: editing the template later
    never changes an evaluation already created against it."""

    __tablename__ = "evaluations"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "period_id", "kind", name="uq_evaluations_employee_period_kind"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id"), index=True)
    period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incentive_periods.id"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=EvaluationStatus.DRAFT.value)
    template_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kpi_template_versions.id")
    )
    # Who may edit while draft/returned: the assigned reviewer for `regular`,
    # the employee's own user account for `self_appraisal`.
    owner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    activities: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    score_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(1), nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, default=1)

    employee: Mapped["Employee"] = relationship()
    template_version: Mapped["KpiTemplateVersion"] = relationship()
    scores: Mapped[list["EvaluationScore"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationScore(Base, TimestampMixin):
    __tablename__ = "evaluation_scores"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_id", "criterion_id", name="uq_evaluation_scores_eval_criterion"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("evaluations.id"), index=True)
    criterion_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kpi_criteria.id"))
    raw_input: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    awarded_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    # Retained for audit diff even after the reviewer overrides it — never
    # overwritten once computed at evaluation-creation time.
    auto_suggested_marks: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship(back_populates="scores")
    criterion: Mapped["KpiCriterion"] = relationship()
