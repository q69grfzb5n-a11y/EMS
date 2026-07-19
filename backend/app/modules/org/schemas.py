from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class DepartmentOut(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: str
    is_active: bool


class DepartmentCreateRequest(BaseModel):
    code: str
    name_en: str
    name_ar: str


class DepartmentPatchRequest(BaseModel):
    name_en: str | None = None
    name_ar: str | None = None
    is_active: bool | None = None


class PositionRateOut(BaseModel):
    id: int
    position_id: int
    effective_from: date
    effective_to: date | None
    incentive_pct: Decimal | None
    flat_ref_amount: Decimal | None


class PositionRateCreateRequest(BaseModel):
    effective_from: date
    effective_to: date | None = None
    incentive_pct: Decimal | None = Field(default=None, ge=0, le=1)
    flat_ref_amount: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _at_least_one_rate(self) -> "PositionRateCreateRequest":
        if self.incentive_pct is None and self.flat_ref_amount is None:
            raise ValueError("Provide incentive_pct and/or flat_ref_amount")
        return self


class PositionOut(BaseModel):
    id: int
    code: str
    title_en: str
    title_ar: str
    is_active: bool
    current_rate: PositionRateOut | None = None


class PositionCreateRequest(BaseModel):
    code: str
    title_en: str
    title_ar: str


class PositionPatchRequest(BaseModel):
    title_en: str | None = None
    title_ar: str | None = None
    is_active: bool | None = None
