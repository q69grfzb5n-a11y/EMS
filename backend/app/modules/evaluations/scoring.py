"""Pure evaluation scoring: raw input -> awarded marks -> overall score_pct +
an informational grade. Zero DB access."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# Verified against the legacy workbook (PLAN §3.1, /5 bands 4.5/3/2 restated as
# percentages): A >=0.90, B >=0.60, C >=0.40, D <0.40.
GRADE_BANDS: tuple[tuple[Decimal, str], ...] = (
    (Decimal("0.90"), "A"),
    (Decimal("0.60"), "B"),
    (Decimal("0.40"), "C"),
)
DEFAULT_GRADE = "D"


def awarded_marks_for_input(
    *, input_mode: str, raw_input: Decimal | None, max_marks: int, allow_negative: bool
) -> Decimal | None:
    """marks mode: awarded = raw_input directly. scale_1_5 mode: awarded =
    rank/5 * max_marks (the legacy weights-as-marks mapping, PLAN §2)."""
    if raw_input is None:
        return None
    if input_mode == "scale_1_5":
        awarded = (raw_input / Decimal(5)) * Decimal(max_marks)
    else:
        awarded = raw_input
    if not allow_negative and awarded < 0:
        awarded = Decimal(0)
    return awarded.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ScoreSummary:
    score_pct: Decimal
    grade: str


def summarize_scores(awarded_and_max: list[tuple[Decimal | None, int]]) -> ScoreSummary:
    """awarded_and_max: [(awarded_marks_or_None, criterion_max_marks), ...] for
    every criterion on the evaluation's pinned template version. Unscored
    criteria (None) count as 0 toward the total, never block the overall
    percentage from being computed."""
    total_max = sum(max_marks for _, max_marks in awarded_and_max)
    total_awarded = sum((awarded or Decimal(0)) for awarded, _ in awarded_and_max)
    if total_max <= 0:
        return ScoreSummary(score_pct=Decimal(0), grade=DEFAULT_GRADE)

    pct = max(Decimal(total_awarded), Decimal(0)) / Decimal(total_max)
    pct = pct.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    for threshold, grade in GRADE_BANDS:
        if pct >= threshold:
            return ScoreSummary(score_pct=pct, grade=grade)
    return ScoreSummary(score_pct=pct, grade=DEFAULT_GRADE)
