from datetime import date
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import AutoSource, InputMode, TemplateVersionStatus
from app.db.base import Base, TimestampMixin
from app.modules.org.models import Position


class KpiTemplate(Base, TimestampMixin):
    """Logical template identity — stable across versions (e.g. 'SKILLED')."""

    __tablename__ = "kpi_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(150))
    name_ar: Mapped[str] = mapped_column(String(150))

    versions: Mapped[list["KpiTemplateVersion"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class KpiTemplateVersion(Base, TimestampMixin):
    """draft -> active -> archived. At most one active version per template
    (partial unique index below); used versions are never edited again."""

    __tablename__ = "kpi_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_no", name="uq_kpi_template_versions_version_no"),
        Index(
            "uq_kpi_template_versions_one_active",
            "template_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kpi_templates.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=TemplateVersionStatus.DRAFT.value)

    template: Mapped["KpiTemplate"] = relationship(back_populates="versions")
    criteria: Mapped[list["KpiCriterion"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="KpiCriterion.sort_order",
    )


class KpiCriterion(Base, TimestampMixin):
    __tablename__ = "kpi_criteria"
    __table_args__ = (CheckConstraint("max_marks > 0", name="max_marks_positive"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kpi_template_versions.id")
    )
    name_en: Mapped[str] = mapped_column(String(200))
    name_ar: Mapped[str] = mapped_column(String(200))
    guidance_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    guidance_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_marks: Mapped[int] = mapped_column(SmallInteger)
    input_mode: Mapped[str] = mapped_column(String(20), default=InputMode.MARKS.value)
    allow_negative: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_source: Mapped[str] = mapped_column(String(20), default=AutoSource.NONE.value)
    auto_params: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    version: Mapped["KpiTemplateVersion"] = relationship(back_populates="criteria")


class KpiTemplateAssignment(Base, TimestampMixin):
    """Temporal: one non-overlapping window per position (GiST EXCLUDE, see migration).
    Pins the logical template only — the active version at evaluation-creation time
    is what Phase 5 will pin onto the evaluation itself."""

    __tablename__ = "kpi_template_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    position_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("positions.id"), index=True)
    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("kpi_templates.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    position: Mapped["Position"] = relationship()
    template: Mapped["KpiTemplate"] = relationship()
