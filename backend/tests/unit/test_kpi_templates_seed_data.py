import json
from pathlib import Path

SEED_FILE = Path(__file__).resolve().parents[2] / "app" / "db" / "seed_data" / "kpi_templates.json"


def test_all_seed_templates_have_criteria_summing_to_100() -> None:
    templates = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    assert len(templates) == 4

    for template in templates:
        total = sum(c["max_marks"] for c in template["criteria"])
        assert total == 100, f"{template['code']} sums to {total}, not 100"


def test_seed_template_codes_are_unique() -> None:
    templates = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    codes = [t["code"] for t in templates]
    assert len(codes) == len(set(codes))
