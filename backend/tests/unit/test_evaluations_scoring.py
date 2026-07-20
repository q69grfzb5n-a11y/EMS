from decimal import Decimal

from app.modules.evaluations.scoring import awarded_marks_for_input, summarize_scores


def test_awarded_marks_marks_mode_is_raw_input_directly() -> None:
    result = awarded_marks_for_input(
        input_mode="marks", raw_input=Decimal(25), max_marks=30, allow_negative=False
    )
    assert result == Decimal("25.00")


def test_awarded_marks_marks_mode_negative_clamped_when_not_allowed() -> None:
    result = awarded_marks_for_input(
        input_mode="marks", raw_input=Decimal(-5), max_marks=10, allow_negative=False
    )
    assert result == Decimal("0.00")


def test_awarded_marks_marks_mode_negative_kept_when_allowed() -> None:
    result = awarded_marks_for_input(
        input_mode="marks", raw_input=Decimal(-5), max_marks=10, allow_negative=True
    )
    assert result == Decimal("-5.00")


def test_awarded_marks_scale_1_5_mode_maps_rank_to_marks() -> None:
    # rank 4 out of 5, max_marks 30 -> 4/5 * 30 = 24
    result = awarded_marks_for_input(
        input_mode="scale_1_5", raw_input=Decimal(4), max_marks=30, allow_negative=False
    )
    assert result == Decimal("24.00")


def test_awarded_marks_none_when_unscored() -> None:
    result = awarded_marks_for_input(
        input_mode="marks", raw_input=None, max_marks=10, allow_negative=False
    )
    assert result is None


def test_summarize_scores_clamps_total_at_zero_not_per_criterion() -> None:
    result = summarize_scores([(Decimal(-5), 10), (Decimal(-10), 10)])
    assert result.score_pct == Decimal("0.0000")
    assert result.grade == "D"


def test_summarize_scores_grade_bands() -> None:
    assert summarize_scores([(Decimal(95), 100)]).grade == "A"
    assert summarize_scores([(Decimal(70), 100)]).grade == "B"
    assert summarize_scores([(Decimal(50), 100)]).grade == "C"
    assert summarize_scores([(Decimal(30), 100)]).grade == "D"


def test_summarize_scores_boundary_is_inclusive() -> None:
    assert summarize_scores([(Decimal(90), 100)]).grade == "A"
    assert summarize_scores([(Decimal(60), 100)]).grade == "B"
    assert summarize_scores([(Decimal(40), 100)]).grade == "C"


def test_summarize_scores_unscored_criteria_count_as_zero() -> None:
    result = summarize_scores([(Decimal(50), 50), (None, 50)])
    assert result.score_pct == Decimal("0.5000")


def test_summarize_scores_no_criteria_is_zero_pct_grade_d() -> None:
    result = summarize_scores([])
    assert result.score_pct == Decimal(0)
    assert result.grade == "D"
