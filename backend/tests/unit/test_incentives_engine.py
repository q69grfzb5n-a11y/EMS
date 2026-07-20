"""Golden tests for the pure incentive engine, hand-verified against real cached
values from docs/source/Precast Incentives 03-2026.xlsm ("Production" sheet,
rows 8-12, March-2026 column pair AF/AG — target_pool=4,300,000,
actual_pool=3,191,117.5778710945). See docs/calculation-engine.md."""

from decimal import Decimal

import pytest

from app.modules.incentives.engine import (
    LEGACY_FLAT,
    PCT_OF_SALARY,
    LineInputs,
    RunParams,
    compute_line,
    round_step,
)

TARGET_RATIO = Decimal("3191117.5778710945") / Decimal("4300000")
DEFAULT_PARAMS = RunParams()


def _legacy_line(evaluation_pct: str, flat_ref_amount: str) -> LineInputs:
    return LineInputs(
        evaluation_pct=Decimal(evaluation_pct),
        formula_mode=LEGACY_FLAT,
        flat_ref_amount=Decimal(flat_ref_amount),
        attendance_factor=Decimal(1),
        target_ratio=TARGET_RATIO,
    )


# ---- golden rows from the real workbook ------------------------------------


def test_golden_row8_fabricator_ocampo() -> None:
    result = compute_line(_legacy_line("0.97", "1000"), DEFAULT_PARAMS)
    assert result.computed_amount == Decimal(720)


def test_golden_row9_foreman2() -> None:
    result = compute_line(_legacy_line("0.8", "1300"), DEFAULT_PARAMS)
    assert result.computed_amount == Decimal(780)


def test_golden_row10_fabricator() -> None:
    result = compute_line(_legacy_line("0.9", "1000"), DEFAULT_PARAMS)
    assert result.computed_amount == Decimal(670)


def test_golden_row11_fabricator() -> None:
    result = compute_line(_legacy_line("0.9", "1000"), DEFAULT_PARAMS)
    assert result.computed_amount == Decimal(670)


def test_golden_row12_welder() -> None:
    result = compute_line(_legacy_line("0.9", "850"), DEFAULT_PARAMS)
    assert result.computed_amount == Decimal(570)


def test_golden_row8_position_ref_and_raw_amount_are_exposed() -> None:
    result = compute_line(_legacy_line("0.97", "1000"), DEFAULT_PARAMS)
    assert result.position_ref == Decimal(1000)
    assert result.raw_amount == Decimal("0.97") * Decimal(1000) * Decimal(1) * TARGET_RATIO


# ---- rounding edges ----------------------------------------------------------


def test_round_step_exact_multiple_unchanged() -> None:
    assert round_step(Decimal(720), step=Decimal(10), mode="CEILING") == Decimal(720)


def test_round_step_zero_stays_zero() -> None:
    assert round_step(Decimal(0), step=Decimal(10), mode="CEILING") == Decimal(0)


def test_round_step_ceiling_rounds_up_to_next_multiple() -> None:
    assert round_step(Decimal("711.01"), step=Decimal(10), mode="CEILING") == Decimal(720)


def test_round_step_ceiling_on_negative_rounds_toward_zero() -> None:
    assert round_step(Decimal(-5), step=Decimal(10), mode="CEILING") == Decimal(0)


def test_round_step_rejects_nonpositive_step() -> None:
    with pytest.raises(ValueError, match="step must be positive"):
        round_step(Decimal(10), step=Decimal(0), mode="CEILING")


def test_round_step_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="unsupported rounding mode"):
        round_step(Decimal(10), step=Decimal(10), mode="BANKERS")


# ---- both formula modes -----------------------------------------------------


def test_pct_of_salary_mode() -> None:
    inputs = LineInputs(
        evaluation_pct=Decimal("0.85"),
        formula_mode=PCT_OF_SALARY,
        base_salary=Decimal(2000),
        position_incentive_pct=Decimal("0.15"),
        attendance_factor=Decimal(1),
        target_ratio=Decimal("0.7218"),
    )
    result = compute_line(inputs, DEFAULT_PARAMS)
    # 0.85 * (2000*0.15) * 1 * 0.7218 = 0.85*300*0.7218 = 184.059 -> ceil10 = 190
    assert result.position_ref == Decimal(300)
    assert result.computed_amount == Decimal(190)


def test_legacy_flat_mode_matches_plan_worked_example() -> None:
    # PLAN.md's own worked example: 0.85 x 2000 x 1 x 0.7218 -> ceil10 = 1230
    inputs = LineInputs(
        evaluation_pct=Decimal("0.85"),
        formula_mode=LEGACY_FLAT,
        flat_ref_amount=Decimal(2000),
        attendance_factor=Decimal(1),
        target_ratio=Decimal("0.7218"),
    )
    result = compute_line(inputs, DEFAULT_PARAMS)
    assert result.computed_amount == Decimal(1230)


def test_pct_of_salary_requires_salary_and_position_pct() -> None:
    inputs = LineInputs(
        evaluation_pct=Decimal("0.85"),
        formula_mode=PCT_OF_SALARY,
        attendance_factor=Decimal(1),
        target_ratio=Decimal(1),
    )
    with pytest.raises(ValueError, match="base_salary and position_incentive_pct"):
        compute_line(inputs, DEFAULT_PARAMS)


def test_legacy_flat_requires_flat_ref_amount() -> None:
    inputs = LineInputs(
        evaluation_pct=Decimal("0.85"),
        formula_mode=LEGACY_FLAT,
        attendance_factor=Decimal(1),
        target_ratio=Decimal(1),
    )
    with pytest.raises(ValueError, match="flat_ref_amount is required"):
        compute_line(inputs, DEFAULT_PARAMS)


def test_unknown_formula_mode_rejected() -> None:
    inputs = LineInputs(
        evaluation_pct=Decimal("0.85"),
        formula_mode="made_up_mode",
        attendance_factor=Decimal(1),
        target_ratio=Decimal(1),
    )
    with pytest.raises(ValueError, match="unknown formula_mode"):
        compute_line(inputs, DEFAULT_PARAMS)


def test_attendance_factor_scales_result() -> None:
    half = compute_line(
        LineInputs(
            evaluation_pct=Decimal(1),
            formula_mode=LEGACY_FLAT,
            flat_ref_amount=Decimal(1000),
            attendance_factor=Decimal("0.5"),
            target_ratio=Decimal(1),
        ),
        DEFAULT_PARAMS,
    )
    full = compute_line(
        LineInputs(
            evaluation_pct=Decimal(1),
            formula_mode=LEGACY_FLAT,
            flat_ref_amount=Decimal(1000),
            attendance_factor=Decimal(1),
            target_ratio=Decimal(1),
        ),
        DEFAULT_PARAMS,
    )
    assert half.computed_amount == Decimal(500)
    assert full.computed_amount == Decimal(1000)
