#!/usr/bin/env python3
"""Assign a KPI template to every position that doesn't have one.

Without an assignment a position's employees can never be evaluated, which
means they produce no incentive line and instead show up as a
`missing_evaluation` exception on every run — so a factory with mostly
unassigned positions produces a run with zero lines and hundreds of
exceptions, which reads as "the calculation is broken" when it is really
"nothing has been configured to evaluate."

Mapping is by seniority/skill, matching how the four real templates are
described in the source workbook:
  KEY_FOREMAN  - leadership: foremen and supervisors
  NON_SKILLED  - manual roles with no trade qualification
  SKILLED      - everything else (trades, technicians, engineers, QC, admin)
LEGACY_TEAM is deliberately never auto-assigned: it is the historical
whole-team scheme and only applies where HR explicitly asks for it.

Idempotent: only positions with no current (open-ended) assignment are
touched, so re-running never duplicates or overwrites a deliberate choice.

Usage: uv run python scripts/assign_kpi_templates.py [--dry-run]
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

import app.modules.employees.models  # noqa: F401  (FK target registration)
from app.db.session import SessionLocal
from app.modules.kpi_templates.models import KpiTemplate, KpiTemplateAssignment
from app.modules.org.models import Position

ASSIGNMENT_EPOCH = date(2020, 1, 1)

KEY_FOREMAN_POSITIONS = {"foreman_1", "foreman_2", "supervisor"}
NON_SKILLED_POSITIONS = {
    "labor",
    "driver_1",
    "driver_2",
    "sandblaster",
    "other",
}


def template_for(position_code: str) -> str:
    if position_code in KEY_FOREMAN_POSITIONS:
        return "KEY_FOREMAN"
    if position_code in NON_SKILLED_POSITIONS:
        return "NON_SKILLED"
    return "SKILLED"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change, write nothing"
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        templates = {t.code: t for t in db.scalars(select(KpiTemplate))}
        missing = {"SKILLED", "NON_SKILLED", "KEY_FOREMAN"} - set(templates)
        if missing:
            print(f"ERROR: expected templates not seeded: {sorted(missing)}", file=sys.stderr)
            print("Run scripts/seed.py --core first.", file=sys.stderr)
            raise SystemExit(1)

        assigned_position_ids = set(
            db.scalars(
                select(KpiTemplateAssignment.position_id).where(
                    KpiTemplateAssignment.effective_to.is_(None)
                )
            )
        )

        created = 0
        skipped = 0
        for position in db.scalars(select(Position).order_by(Position.code)):
            if position.id in assigned_position_ids:
                skipped += 1
                continue
            code = template_for(position.code)
            print(f"  + {position.code:<16} -> {code}")
            if not args.dry_run:
                db.add(
                    KpiTemplateAssignment(
                        position_id=position.id,
                        template_id=templates[code].id,
                        effective_from=ASSIGNMENT_EPOCH,
                    )
                )
            created += 1

        if args.dry_run:
            print(f"\nDRY RUN: {created} would be assigned, {skipped} already had one.")
        else:
            db.commit()
            print(f"\nDone: {created} positions assigned, {skipped} already had one.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
