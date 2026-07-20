from io import BytesIO

import openpyxl

from app.modules.attendance.importer import (
    EXPECTED_HEADERS,
    REQUIRED_SHEET_NAME,
    normalize_staff_no,
    parse_attendance_file,
)

# June 2026 has 30 days — every fixture row below is built to sum to that
# unless a test deliberately wants a bucket mismatch.
DECLARED_YEAR = 2026
DECLARED_MONTH = 6
DAYS_IN_MONTH = 30


def _happy_row(person_no: object = 1001, month: str = "06-2026") -> list[object]:
    # present + off_days + absent + leave + public_holiday == 30
    return [
        month,
        person_no,
        "DOE, JOHN",
        "Dept",
        "Site",
        "SAJCO",
        22,
        4,
        2,
        2,
        0,
        0,
        5.5,
        22,
        0,
        0,
        5.5,
    ]


def _build_workbook(
    rows: list[list[object]],
    *,
    sheet_name: str = REQUIRED_SHEET_NAME,
    header: list[object] | None = None,
) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(header if header is not None else list(EXPECTED_HEADERS))
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_normalize_staff_no_handles_int_and_string() -> None:
    assert normalize_staff_no(1006) == "1006"
    assert normalize_staff_no("1006") == "1006"
    assert normalize_staff_no(" 1006 ") == "1006"


def test_happy_path_parses_one_clean_row() -> None:
    content = _build_workbook([_happy_row()])

    result = parse_attendance_file(
        content, declared_year=DECLARED_YEAR, declared_month=DECLARED_MONTH
    )

    assert result.issues == []
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.staff_no == "1001"
    assert row.present == 22
    assert row.over_time == 5.5


def test_wrong_sheet_name_is_a_single_file_level_error() -> None:
    content = _build_workbook([_happy_row()], sheet_name="Some Other Sheet")

    result = parse_attendance_file(
        content, declared_year=DECLARED_YEAR, declared_month=DECLARED_MONTH
    )

    assert result.rows == []
    assert result.has_errors
    assert "not found" in result.issues[0].message


def test_wrong_header_is_a_single_file_level_error() -> None:
    bad_header = list(EXPECTED_HEADERS)
    bad_header[0] = "Period"  # drift on the very first column
    content = _build_workbook([_happy_row()], header=bad_header)

    result = parse_attendance_file(
        content, declared_year=DECLARED_YEAR, declared_month=DECLARED_MONTH
    )

    assert result.rows == []
    assert result.has_errors
    assert "Header drift" in result.issues[0].message


def test_bad_month_row_is_rejected() -> None:
    content = _build_workbook([_happy_row(month="05-2026")])

    result = parse_attendance_file(
        content, declared_year=DECLARED_YEAR, declared_month=DECLARED_MONTH
    )

    assert result.rows == []
    assert result.has_errors
    assert "does not match declared period" in result.issues[0].message


def test_duplicate_staff_no_keeps_first_row_flags_second() -> None:
    content = _build_workbook([_happy_row(person_no=2001), _happy_row(person_no=2001)])

    result = parse_attendance_file(
        content, declared_year=DECLARED_YEAR, declared_month=DECLARED_MONTH
    )

    assert len(result.rows) == 1
    assert result.has_errors
    assert any("Duplicate" in i.message for i in result.issues)


def test_bucket_sum_mismatch_is_a_warning_not_an_error() -> None:
    row = _happy_row()
    row[6] = 25  # present bumped up, bucket now sums to 33 instead of 30
    content = _build_workbook([row])

    result = parse_attendance_file(
        content, declared_year=DECLARED_YEAR, declared_month=DECLARED_MONTH
    )

    assert len(result.rows) == 1  # row is kept
    assert not result.has_errors  # only a warning
    assert any(i.severity == "warning" and "expected 30 days" in i.message for i in result.issues)


def test_blank_trailer_rows_are_skipped() -> None:
    content = _build_workbook([_happy_row(), [None] * 17])

    result = parse_attendance_file(
        content, declared_year=DECLARED_YEAR, declared_month=DECLARED_MONTH
    )

    assert len(result.rows) == 1
    assert result.issues == []
