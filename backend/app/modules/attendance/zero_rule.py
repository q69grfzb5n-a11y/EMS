"""Pure 6-month zero-attendance rule: rolling leave+absence vs contract
allowance. Zero DB access — the service layer gathers trailing period
attendance and passes it in.
"""

from dataclasses import dataclass

# 45 days/1-year contract, 90 days/2-year contract — the only two contract
# lengths this system knows about (see employees.contract_years).
ALLOWANCE_DAYS_BY_CONTRACT_YEARS: dict[int, int] = {1: 45, 2: 90}


@dataclass(frozen=True)
class PeriodAttendance:
    period_id: int
    leave_days: int
    absent_days: int


@dataclass(frozen=True)
class ZeroRuleResult:
    breached: bool
    period_from_id: int
    period_to_id: int
    total_leave_absence_days: int
    allowance_days: int


def evaluate_zero_rule(
    *, contract_years: int | None, trailing_periods: list[PeriodAttendance]
) -> ZeroRuleResult | None:
    """trailing_periods: oldest first, up to the 6 most recent periods with
    attendance data for this employee. Returns None when there's nothing to
    evaluate yet, or when contract_years is missing/unrecognized — callers
    must treat that as "can't tell, report it", never assume an allowance."""
    if not trailing_periods:
        return None
    allowance = (
        ALLOWANCE_DAYS_BY_CONTRACT_YEARS.get(contract_years) if contract_years is not None else None
    )
    if allowance is None:
        return None

    total = sum(p.leave_days + p.absent_days for p in trailing_periods)
    return ZeroRuleResult(
        breached=total > allowance,
        period_from_id=trailing_periods[0].period_id,
        period_to_id=trailing_periods[-1].period_id,
        total_leave_absence_days=total,
        allowance_days=allowance,
    )
