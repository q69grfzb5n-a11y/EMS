"""Finance Excel export — pure: builds an openpyxl Workbook from already-loaded
domain data, zero DB access of its own. A "Summary" sheet (grand totals per
department) plus one sheet per department listing its payouts, both RTL for
the real Arabic names (PLAN §Phase 8)."""

from dataclasses import dataclass
from decimal import Decimal

import openpyxl
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

_HEADER_FONT = Font(bold=True)


@dataclass(frozen=True)
class PayoutRow:
    department_code: str
    department_name_en: str
    department_name_ar: str
    staff_no: str
    full_name_en: str | None
    full_name_ar: str
    evaluation_pct: Decimal
    final_amount: Decimal


def _write_header(ws: Worksheet, headers: list[str]) -> None:
    ws.append(headers)
    for cell in ws[1]:
        cell.font = _HEADER_FONT


def build_finance_workbook(
    *, run_no: int, year: int, month: int, rows: list[PayoutRow]
) -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    summary_ws = wb.active
    assert summary_ws is not None
    summary_ws.title = "Summary"
    summary_ws.sheet_view.rightToLeft = True
    summary_ws.append([f"Incentive Payout — Run #{run_no} — {month:02d}/{year}"])
    summary_ws.append([])
    _write_header(summary_ws, ["Department (EN)", "القسم", "Employees", "Total (SAR)"])

    by_dept: dict[str, list[PayoutRow]] = {}
    for row in rows:
        by_dept.setdefault(row.department_code, []).append(row)

    grand_total = Decimal(0)
    for dept_code in sorted(by_dept):
        dept_rows = by_dept[dept_code]
        dept_total = sum((r.final_amount for r in dept_rows), Decimal(0))
        grand_total += dept_total
        summary_ws.append(
            [
                dept_rows[0].department_name_en,
                dept_rows[0].department_name_ar,
                len(dept_rows),
                float(dept_total),
            ]
        )
    summary_ws.append(["Grand Total", "الإجمالي", len(rows), float(grand_total)])
    for cell in summary_ws[summary_ws.max_row]:
        cell.font = _HEADER_FONT

    for dept_code in sorted(by_dept):
        dept_rows = by_dept[dept_code]
        ws = wb.create_sheet(title=dept_code[:31])
        ws.sheet_view.rightToLeft = True
        _write_header(ws, ["Staff No", "Name (EN)", "الاسم", "Evaluation %", "Amount (SAR)"])
        for r in sorted(dept_rows, key=lambda x: x.staff_no):
            ws.append(
                [
                    r.staff_no,
                    r.full_name_en or "",
                    r.full_name_ar,
                    float(r.evaluation_pct) * 100,
                    float(r.final_amount),
                ]
            )

    return wb
