from app.modules.reports.blank_template import (
    CriterionSpec,
    RosterMember,
    build_blank_evaluation_workbook,
)


def test_header_row_includes_criteria_with_max_marks() -> None:
    criteria = [
        CriterionSpec(name_en="Quality", name_ar="الجودة", max_marks=30, input_mode="marks"),
        CriterionSpec(name_en="Safety", name_ar="السلامة", max_marks=10, input_mode="scale_1_5"),
    ]
    wb = build_blank_evaluation_workbook(template_name_en="Skilled", criteria=criteria, roster=[])

    header = [cell.value for cell in next(wb.active.iter_rows(min_row=1, max_row=1))]
    assert header == ["Staff No", "Name (EN)", "الاسم", "Quality (30)", "Safety (10)"]


def test_roster_rows_prefilled_with_real_employees() -> None:
    criteria = [
        CriterionSpec(name_en="Quality", name_ar="الجودة", max_marks=30, input_mode="marks")
    ]
    roster = [
        RosterMember(staff_no="1001", full_name_en="Employee 1001", full_name_ar="اسم ١"),
        RosterMember(staff_no="1002", full_name_en="Employee 1002", full_name_ar="اسم ٢"),
    ]
    wb = build_blank_evaluation_workbook(
        template_name_en="Skilled", criteria=criteria, roster=roster
    )

    data_rows = list(wb.active.iter_rows(min_row=2, values_only=True))
    assert data_rows[0][0] == "1001"
    assert data_rows[1][0] == "1002"
    # score column left blank for hand-filling
    assert data_rows[0][3] is None


def test_empty_roster_still_produces_one_fillable_row() -> None:
    criteria = [
        CriterionSpec(name_en="Quality", name_ar="الجودة", max_marks=30, input_mode="marks")
    ]
    wb = build_blank_evaluation_workbook(template_name_en="Skilled", criteria=criteria, roster=[])

    data_rows = list(wb.active.iter_rows(min_row=2, values_only=True))
    assert len(data_rows) == 1


def test_data_validation_range_matches_max_marks_for_marks_mode() -> None:
    criteria = [
        CriterionSpec(name_en="Quality", name_ar="الجودة", max_marks=30, input_mode="marks")
    ]
    roster = [RosterMember(staff_no="1001", full_name_en="E", full_name_ar="ا")]
    wb = build_blank_evaluation_workbook(
        template_name_en="Skilled", criteria=criteria, roster=roster
    )

    validations = list(wb.active.data_validations.dataValidation)
    assert len(validations) == 1
    assert validations[0].formula1 == "0"
    assert validations[0].formula2 == "30"


def test_data_validation_range_is_1_to_5_for_scale_mode() -> None:
    criteria = [
        CriterionSpec(name_en="Safety", name_ar="السلامة", max_marks=10, input_mode="scale_1_5")
    ]
    roster = [RosterMember(staff_no="1001", full_name_en="E", full_name_ar="ا")]
    wb = build_blank_evaluation_workbook(
        template_name_en="Skilled", criteria=criteria, roster=roster
    )

    validations = list(wb.active.data_validations.dataValidation)
    assert validations[0].formula1 == "1"
    assert validations[0].formula2 == "5"


def test_sheet_is_rtl_and_title_truncated_to_31_chars() -> None:
    long_name = "A" * 50
    wb = build_blank_evaluation_workbook(template_name_en=long_name, criteria=[], roster=[])
    assert wb.active.sheet_view.rightToLeft is True
    assert len(wb.active.title) <= 31
