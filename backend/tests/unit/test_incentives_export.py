from decimal import Decimal

from app.modules.incentives.export import PayoutRow, build_finance_workbook


def _row(dept_code: str, dept_en: str, dept_ar: str, staff_no: str, amount: str) -> PayoutRow:
    return PayoutRow(
        department_code=dept_code,
        department_name_en=dept_en,
        department_name_ar=dept_ar,
        staff_no=staff_no,
        full_name_en=f"Employee {staff_no}",
        full_name_ar="اسم الموظف",
        evaluation_pct=Decimal("0.9"),
        final_amount=Decimal(amount),
    )


def test_summary_sheet_totals_equal_sum_of_line_items() -> None:
    rows = [
        _row("PROD", "Production", "الإنتاج", "1001", "720"),
        _row("PROD", "Production", "الإنتاج", "1002", "580"),
        _row("QC", "Quality Control", "مراقبة الجودة", "2001", "410"),
    ]
    wb = build_finance_workbook(run_no=5, year=2026, month=6, rows=rows)

    summary = wb["Summary"]
    values = [tuple(cell.value for cell in row) for row in summary.iter_rows()]
    grand_total_row = values[-1]
    assert grand_total_row[0] == "Grand Total"
    assert grand_total_row[2] == 3
    assert grand_total_row[3] == 720 + 580 + 410


def test_one_sheet_per_department_plus_summary() -> None:
    rows = [
        _row("PROD", "Production", "الإنتاج", "1001", "720"),
        _row("QC", "Quality Control", "مراقبة الجودة", "2001", "410"),
    ]
    wb = build_finance_workbook(run_no=1, year=2026, month=6, rows=rows)

    assert wb.sheetnames == ["Summary", "PROD", "QC"]


def test_department_sheet_lists_its_own_rows_only() -> None:
    rows = [
        _row("PROD", "Production", "الإنتاج", "1001", "720"),
        _row("QC", "Quality Control", "مراقبة الجودة", "2001", "410"),
    ]
    wb = build_finance_workbook(run_no=1, year=2026, month=6, rows=rows)

    prod_ws = wb["PROD"]
    data_rows = list(prod_ws.iter_rows(min_row=2, values_only=True))
    assert len(data_rows) == 1
    assert data_rows[0][0] == "1001"


def test_sheets_are_rtl_oriented() -> None:
    rows = [_row("PROD", "Production", "الإنتاج", "1001", "720")]
    wb = build_finance_workbook(run_no=1, year=2026, month=6, rows=rows)

    assert wb["Summary"].sheet_view.rightToLeft is True
    assert wb["PROD"].sheet_view.rightToLeft is True


def test_header_row_is_bold() -> None:
    rows = [_row("PROD", "Production", "الإنتاج", "1001", "720")]
    wb = build_finance_workbook(run_no=1, year=2026, month=6, rows=rows)

    header_row = list(wb["PROD"].iter_rows(min_row=1, max_row=1))[0]
    assert all(cell.font.bold for cell in header_row)


def test_empty_rows_produce_only_the_summary_sheet() -> None:
    wb = build_finance_workbook(run_no=1, year=2026, month=6, rows=[])
    assert wb.sheetnames == ["Summary"]
