# Calculation Engine

> Status: skeleton — worked examples and goldens are added in Phase 7. Formula source of truth: [PLAN.md §3.1, §6.2](../PLAN.md).

## Formula (dual-mode)

- **`pct_of_salary`**: `bonus = evaluationPct × (baseSalary × positionIncentivePct) × attendanceFactor × budgetTargetRatio`
- **`legacy_flat`**: `bonus = evaluationPct × flatRefAmount × attendanceFactor × budgetTargetRatio`
- Rounding: `CEILING` to nearest 10 SAR (configurable via `app_settings.rounding_step` / `rounding_mode`).

## Worked examples

_To add once `backend/app/modules/incentives/engine.py` lands (Phase 7), with hand-verified rows from the recomputed March-2026 workbook._

## Golden test policy

Engine tests reproduce the recomputed March-2026 workbook incentive column row-for-row (Decimal math only, no floats). Historical month columns in the source workbook are pasted values, not live formulas — goldens must be validated against a recomputed copy with PMO before Phase 7 sign-off.
