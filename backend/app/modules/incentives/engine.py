"""Pure incentive calculation engine — no SQLAlchemy, no DB access, Decimal-only.
Reproduces the legacy workbook formula exactly (see docs/calculation-engine.md
and PLAN.md §3.1, §6.2):

    incentive = round_step(
        evaluationPct × positionRef × attendanceFactor × targetRatio, 10, CEILING
    )

`positionRef` is resolved from one of two dual-mode inputs: the legacy flat SAR
reference amount (`legacy_flat`), or `baseSalary × positionIncentivePct`
(`pct_of_salary`, usable once HR loads real base salaries).
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

LEGACY_FLAT = "legacy_flat"
PCT_OF_SALARY = "pct_of_salary"
FORMULA_MODES = frozenset({LEGACY_FLAT, PCT_OF_SALARY})

_ROUND_MODES = {"CEILING": ROUND_CEILING, "FLOOR": ROUND_FLOOR}


@dataclass(frozen=True)
class LineInputs:
    evaluation_pct: Decimal
    formula_mode: str
    attendance_factor: Decimal
    target_ratio: Decimal
    flat_ref_amount: Decimal | None = None
    base_salary: Decimal | None = None
    position_incentive_pct: Decimal | None = None


@dataclass(frozen=True)
class RunParams:
    rounding_step: Decimal = Decimal(10)
    rounding_mode: str = "CEILING"


@dataclass(frozen=True)
class LineResult:
    position_ref: Decimal
    raw_amount: Decimal
    computed_amount: Decimal


def round_step(x: Decimal, *, step: Decimal, mode: str) -> Decimal:
    if step <= 0:
        raise ValueError("step must be positive")
    if mode not in _ROUND_MODES:
        raise ValueError(f"unsupported rounding mode: {mode!r}")
    quotient = (x / step).to_integral_value(rounding=_ROUND_MODES[mode])
    return quotient * step


def _resolve_position_ref(inputs: LineInputs) -> Decimal:
    if inputs.formula_mode == LEGACY_FLAT:
        if inputs.flat_ref_amount is None:
            raise ValueError("flat_ref_amount is required for legacy_flat mode")
        return inputs.flat_ref_amount
    if inputs.formula_mode == PCT_OF_SALARY:
        if inputs.base_salary is None or inputs.position_incentive_pct is None:
            raise ValueError(
                "base_salary and position_incentive_pct are required for pct_of_salary mode"
            )
        return inputs.base_salary * inputs.position_incentive_pct
    raise ValueError(f"unknown formula_mode: {inputs.formula_mode!r}")


def compute_line(inputs: LineInputs, params: RunParams) -> LineResult:
    position_ref = _resolve_position_ref(inputs)
    raw_amount = (
        inputs.evaluation_pct * position_ref * inputs.attendance_factor * inputs.target_ratio
    )
    computed_amount = round_step(raw_amount, step=params.rounding_step, mode=params.rounding_mode)
    return LineResult(
        position_ref=position_ref, raw_amount=raw_amount, computed_amount=computed_amount
    )
