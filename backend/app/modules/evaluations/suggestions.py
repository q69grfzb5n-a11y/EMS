"""Pure attendance -> KPI-criterion suggestions (zero DB access). Suggestions
pre-fill a criterion's marks at evaluation-creation time; the reviewer's own
entry is always authoritative afterward — this module is never consulted
again once an evaluation exists (see auto_suggested_marks vs awarded_marks
on EvaluationScore)."""

from decimal import Decimal
from typing import Any


def suggest_overtime_marks(
    approved_over_time_hours: Decimal, *, unit_hours: int, points_per_unit: int, max_marks: int
) -> Decimal:
    """1 point per `unit_hours` of approved OT, capped at max_marks."""
    units = int(approved_over_time_hours // unit_hours)
    return min(Decimal(units * points_per_unit), Decimal(max_marks))


def suggest_absence_marks(
    *, max_marks: int, absent_days: int, penalty_per_absence: int, zero_flag_active: bool
) -> Decimal:
    """max_marks - penalty_per_absence * absent_days — may go negative. Forced
    to 0 outright when the employee has an active 6-month zero-attendance flag
    covering this period."""
    if zero_flag_active:
        return Decimal(0)
    return Decimal(max_marks) - Decimal(penalty_per_absence * absent_days)


def suggest_marks(
    *,
    auto_source: str,
    auto_params: dict[str, Any] | None,
    max_marks: int,
    approved_over_time_hours: Decimal | None,
    absent_days: int | None,
    zero_flag_active: bool,
) -> Decimal | None:
    """Dispatches on the criterion's auto_source. Returns None when the
    source doesn't apply or the attendance data needed isn't available —
    callers must leave the criterion unscored, never guess."""
    params = auto_params or {}

    if auto_source == "overtime_hours" and approved_over_time_hours is not None:
        return suggest_overtime_marks(
            approved_over_time_hours,
            unit_hours=int(params.get("unit_hours", 3)),
            points_per_unit=int(params.get("points_per_unit", 1)),
            max_marks=max_marks,
        )

    if auto_source == "absence_penalty" and absent_days is not None:
        return suggest_absence_marks(
            max_marks=max_marks,
            absent_days=absent_days,
            penalty_per_absence=int(params.get("penalty_per_absence", 5)),
            zero_flag_active=zero_flag_active,
        )

    return None
