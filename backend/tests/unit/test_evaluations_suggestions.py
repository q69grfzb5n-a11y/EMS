from decimal import Decimal

from app.modules.evaluations.suggestions import (
    suggest_absence_marks,
    suggest_marks,
    suggest_overtime_marks,
)


def test_suggest_overtime_marks_one_point_per_three_hours() -> None:
    assert suggest_overtime_marks(
        Decimal("9.01"), unit_hours=3, points_per_unit=1, max_marks=30
    ) == Decimal(3)


def test_suggest_overtime_marks_caps_at_max_marks() -> None:
    assert suggest_overtime_marks(
        Decimal("102.49"), unit_hours=3, points_per_unit=1, max_marks=30
    ) == Decimal(30)


def test_suggest_overtime_marks_below_one_unit_is_zero() -> None:
    assert suggest_overtime_marks(
        Decimal("2.9"), unit_hours=3, points_per_unit=1, max_marks=30
    ) == Decimal(0)


def test_suggest_absence_marks_no_absences_is_full_marks() -> None:
    result = suggest_absence_marks(
        max_marks=10, absent_days=0, penalty_per_absence=5, zero_flag_active=False
    )
    assert result == Decimal(10)


def test_suggest_absence_marks_may_go_negative() -> None:
    result = suggest_absence_marks(
        max_marks=10, absent_days=3, penalty_per_absence=5, zero_flag_active=False
    )
    assert result == Decimal(-5)


def test_suggest_absence_marks_forced_zero_under_active_zero_flag() -> None:
    result = suggest_absence_marks(
        max_marks=10, absent_days=0, penalty_per_absence=5, zero_flag_active=True
    )
    assert result == Decimal(0)


def test_suggest_marks_none_source_returns_none() -> None:
    result = suggest_marks(
        auto_source="none",
        auto_params=None,
        max_marks=10,
        approved_over_time_hours=Decimal(9),
        absent_days=0,
        zero_flag_active=False,
    )
    assert result is None


def test_suggest_marks_dispatches_overtime_source() -> None:
    result = suggest_marks(
        auto_source="overtime_hours",
        auto_params={"unit_hours": 3, "points_per_unit": 1},
        max_marks=30,
        approved_over_time_hours=Decimal("9.01"),
        absent_days=None,
        zero_flag_active=False,
    )
    assert result == Decimal(3)


def test_suggest_marks_dispatches_absence_source() -> None:
    result = suggest_marks(
        auto_source="absence_penalty",
        auto_params={"penalty_per_absence": 5},
        max_marks=10,
        approved_over_time_hours=None,
        absent_days=2,
        zero_flag_active=False,
    )
    assert result == Decimal(0)


def test_suggest_marks_returns_none_when_required_data_missing() -> None:
    result = suggest_marks(
        auto_source="overtime_hours",
        auto_params=None,
        max_marks=30,
        approved_over_time_hours=None,
        absent_days=None,
        zero_flag_active=False,
    )
    assert result is None


def test_suggest_marks_uses_default_params_when_missing() -> None:
    result = suggest_marks(
        auto_source="absence_penalty",
        auto_params=None,
        max_marks=10,
        approved_over_time_hours=None,
        absent_days=1,
        zero_flag_active=False,
    )
    assert result == Decimal(5)  # default penalty_per_absence=5
