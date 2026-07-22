"""Golden-file test for Arabic PDF rendering (PLAN §Phase 8): a real Arabic
name must survive into the PDF's actual text layer, not just render as an
image. `pypdf`'s plain extract_text() does not run the BiDi algorithm, so an
RTL run comes back character-reversed ("reshaped") rather than in logical
order — extraction_mode="layout" preserves visual glyph order, which is where
the reversed string is found. This is expected, not a bug in our PDF: it is
exactly the "reshaped strings" PLAN's own test-policy note anticipates."""

from io import BytesIO

from pypdf import PdfReader

from app.modules.reports.pdf import render_pdf

# A real bilingual department name pair, matching Phase 2's real seed data.
REAL_DEPT_NAME_AR = "الإنتاج"  # "Production"


def _extract_layout_text(pdf_bytes: bytes, *, page: int = 0) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return reader.pages[page].extract_text(extraction_mode="layout")


def test_finance_summary_pdf_contains_real_arabic_department_name() -> None:
    context = {
        "run_no": 7,
        "month_str": "06/2026",
        "departments": [
            {"name_ar": REAL_DEPT_NAME_AR, "employee_count": 5, "total_amount": 1000},
        ],
        "grand_total": 1000,
        "total_count": 5,
    }
    pdf_bytes = render_pdf("finance_summary.html", context)

    assert pdf_bytes[:4] == b"%PDF"
    layout_text = _extract_layout_text(pdf_bytes)
    assert REAL_DEPT_NAME_AR[::-1] in layout_text


def test_finance_summary_pdf_contains_ltr_isolated_numbers() -> None:
    context = {
        "run_no": 3,
        "month_str": "06/2026",
        "departments": [{"name_ar": REAL_DEPT_NAME_AR, "employee_count": 12, "total_amount": 4560}],
        "grand_total": 4560,
        "total_count": 12,
    }
    pdf_bytes = render_pdf("finance_summary.html", context)
    layout_text = _extract_layout_text(pdf_bytes)
    assert "4560.00" in layout_text


def test_blank_evaluation_pdf_contains_real_arabic_criterion_name() -> None:
    context = {
        "template_name_ar": "نموذج المهرة",
        "criteria": [{"name_ar": "الجودة", "max_marks": 30}],
        "roster": [{"staff_no": "9001", "full_name_ar": "محمد أحمد"}],
    }
    pdf_bytes = render_pdf("blank_evaluation.html", context)

    assert pdf_bytes[:4] == b"%PDF"
    layout_text = _extract_layout_text(pdf_bytes)
    assert "الجودة"[::-1] in layout_text
    assert "9001" in layout_text


def test_blank_evaluation_pdf_paginates_one_sheet_per_roster_member() -> None:
    context = {
        "template_name_ar": "نموذج المهرة",
        "criteria": [{"name_ar": "الجودة", "max_marks": 30}],
        "roster": [
            {"staff_no": "9001", "full_name_ar": "محمد أحمد"},
            {"staff_no": "9002", "full_name_ar": "علي حسن"},
        ],
    }
    pdf_bytes = render_pdf("blank_evaluation.html", context)
    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) == 2
