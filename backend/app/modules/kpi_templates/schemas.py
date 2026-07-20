from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.common.enums import AutoSource, InputMode


class KpiCriterionOut(BaseModel):
    id: int
    name_en: str
    name_ar: str
    guidance_en: str | None
    guidance_ar: str | None
    max_marks: int
    input_mode: str
    allow_negative: bool
    auto_source: str
    auto_params: dict[str, Any] | None
    sort_order: int


class KpiCriterionCreateRequest(BaseModel):
    name_en: str
    name_ar: str
    guidance_en: str | None = None
    guidance_ar: str | None = None
    max_marks: int = Field(gt=0, le=100)
    input_mode: InputMode = InputMode.MARKS
    allow_negative: bool = False
    auto_source: AutoSource = AutoSource.NONE
    auto_params: dict[str, Any] | None = None
    sort_order: int = 0


class KpiCriterionPatchRequest(BaseModel):
    name_en: str | None = None
    name_ar: str | None = None
    guidance_en: str | None = None
    guidance_ar: str | None = None
    max_marks: int | None = Field(default=None, gt=0, le=100)
    input_mode: InputMode | None = None
    allow_negative: bool | None = None
    auto_source: AutoSource | None = None
    auto_params: dict[str, Any] | None = None
    sort_order: int | None = None


class KpiTemplateVersionOut(BaseModel):
    id: int
    template_id: int
    version_no: int
    status: str
    criteria: list[KpiCriterionOut]
    total_marks: int


class KpiTemplateVersionSummary(BaseModel):
    id: int
    version_no: int
    status: str
    total_marks: int


class CloneVersionRequest(BaseModel):
    source_version_id: int | None = None


class KpiTemplateOut(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: str
    active_version: KpiTemplateVersionSummary | None = None


class KpiTemplateCreateRequest(BaseModel):
    code: str
    name_en: str
    name_ar: str


class KpiTemplateAssignmentOut(BaseModel):
    id: int
    position_id: int
    template_id: int
    effective_from: date
    effective_to: date | None


class KpiTemplateAssignmentCreateRequest(BaseModel):
    template_id: int
    effective_from: date
    effective_to: date | None = None
