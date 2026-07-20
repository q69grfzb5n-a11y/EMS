from app.modules.attendance.zero_rule import PeriodAttendance, evaluate_zero_rule


def test_no_trailing_periods_returns_none() -> None:
    assert evaluate_zero_rule(contract_years=1, trailing_periods=[]) is None


def test_missing_contract_years_returns_none_never_guesses() -> None:
    trailing = [PeriodAttendance(period_id=1, leave_days=10, absent_days=10)]
    assert evaluate_zero_rule(contract_years=None, trailing_periods=trailing) is None


def test_unrecognized_contract_years_returns_none() -> None:
    trailing = [PeriodAttendance(period_id=1, leave_days=10, absent_days=10)]
    assert evaluate_zero_rule(contract_years=3, trailing_periods=trailing) is None


def test_one_year_contract_at_exactly_allowance_is_not_breached() -> None:
    # 45 days exactly — "exceeds" means strictly greater than, not >=.
    trailing = [PeriodAttendance(period_id=1, leave_days=45, absent_days=0)]
    result = evaluate_zero_rule(contract_years=1, trailing_periods=trailing)
    assert result is not None
    assert result.breached is False
    assert result.total_leave_absence_days == 45
    assert result.allowance_days == 45


def test_one_year_contract_one_day_over_allowance_is_breached() -> None:
    trailing = [
        PeriodAttendance(period_id=1, leave_days=20, absent_days=20),
        PeriodAttendance(period_id=2, leave_days=6, absent_days=0),
    ]
    result = evaluate_zero_rule(contract_years=1, trailing_periods=trailing)
    assert result is not None
    assert result.breached is True
    assert result.total_leave_absence_days == 46
    assert result.period_from_id == 1
    assert result.period_to_id == 2


def test_two_year_contract_uses_90_day_allowance() -> None:
    trailing = [PeriodAttendance(period_id=1, leave_days=90, absent_days=1)]
    result = evaluate_zero_rule(contract_years=2, trailing_periods=trailing)
    assert result is not None
    assert result.allowance_days == 90
    assert result.breached is True


def test_window_spans_oldest_to_newest_trailing_period() -> None:
    trailing = [
        PeriodAttendance(period_id=10, leave_days=1, absent_days=0),
        PeriodAttendance(period_id=11, leave_days=1, absent_days=0),
        PeriodAttendance(period_id=12, leave_days=1, absent_days=0),
    ]
    result = evaluate_zero_rule(contract_years=1, trailing_periods=trailing)
    assert result is not None
    assert result.period_from_id == 10
    assert result.period_to_id == 12
    assert result.total_leave_absence_days == 3
