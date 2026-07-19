import openpyxl

from scripts.import_legacy import normalize_staff_no, parse_sheet


def _build_sheet(header: list[str], rows: list[list[object]]):
    wb = openpyxl.Workbook()
    ws = wb.active
    # Rows 1-6 of the real sheets hold title/manager/KPI-weight rows before the
    # actual header on row 7 — pad so parse_sheet's fixed HEADER_ROW/DATA_START_ROW
    # line up the same way they do against the real workbook.
    for _ in range(6):
        ws.append([None] * len(header))
    ws.append(header)
    for row in rows:
        ws.append(row)
    return ws


def test_normalize_staff_no_handles_int_and_padded_string() -> None:
    assert normalize_staff_no(4128) == "4128"
    assert normalize_staff_no("11148") == "11148"
    assert normalize_staff_no(" 4128 ") == "4128"


def test_parse_sheet_resolves_position_and_final_exit_status() -> None:
    header = [
        "No.",
        "Oracle",
        "Employee Name",
        "Position as per Oracle",
        "Actual Position",
        "Actual Position Final",
        "تاريخ الاجازة السنوية",
        "الحالة",
    ]
    ws = _build_sheet(
        header,
        [
            [1, 4128, "اسم الموظف", "نجار", "نجار", "Fabricator", None, "شغال"],
            [
                2,
                4129,
                "موظف اخر",
                "لحام",
                "لحام",
                "Welder",
                None,
                "خروج نهائي اخر عمل له بتاريخ 01/01/2026",
            ],
        ],
    )

    rows, skipped = parse_sheet(ws, "PROD")

    assert skipped == []
    assert len(rows) == 2
    assert rows[0].staff_no == "4128"
    assert rows[0].position_title_raw == "Fabricator"
    assert rows[0].employment_status == "active"
    assert rows[1].employment_status == "terminated"


def test_parse_sheet_reports_missing_position_instead_of_guessing() -> None:
    header = [
        "No.",
        "Oracle",
        "Employee Name",
        "Position as per Oracle",
        "Actual Position Final",
        "الحالة",
    ]
    ws = _build_sheet(header, [[1, 5000, "اسم", "بدون منصب", None, "شغال"]])

    rows, skipped = parse_sheet(ws, "PROD")

    assert rows == []
    assert len(skipped) == 1
    assert skipped[0]["staff_no"] == "5000"
    assert skipped[0]["dept"] == "PROD"


def test_parse_sheet_skips_blank_trailer_rows() -> None:
    header = ["No.", "Oracle", "Employee Name", "Actual Position Final", "الحالة"]
    ws = _build_sheet(
        header,
        [
            [1, 4128, "اسم", "Fabricator", "شغال"],
            [None, None, None, None, None],
        ],
    )

    rows, skipped = parse_sheet(ws, "PROD")

    assert len(rows) == 1
    assert skipped == []


def test_parse_sheet_coalesces_duplicate_position_final_header() -> None:
    # Mirrors the real SCM sheet, which repeats the "Actual Position Final" header
    # across two columns where only one of the two is ever populated per row.
    header = [
        "No.",
        "Oracle",
        "Employee Name",
        "Position as per Oracle",
        "Actual Position",
        "Actual Position Final",
        "Actual Position Final",
        "الحالة",
    ]
    ws = _build_sheet(
        header, [[1, 4128, "اسم", "مراقب توريد", "Foreman 1", "Supervisor", None, "شغال"]]
    )

    rows, skipped = parse_sheet(ws, "SCM")

    assert skipped == []
    assert rows[0].position_title_raw == "Supervisor"
