#!/usr/bin/env python3
"""Link every unlinked login to the employee sharing its staff number.

`users.staff_no` and `employees.staff_no` are the same person's real factory
number, so the match is exact and unambiguous. New accounts are linked
automatically at creation (auth.service.create_user); this script covers
accounts that predate that behaviour or were created directly in the
database.

Why it matters: an unlinked login has no employee, therefore no department —
so a dept_manager sees an empty or unscoped team, a reviewer sees no
assignments, and "my incentives" is always empty. Those all look like
separate bugs but share this one cause.

Idempotent and non-destructive: only touches users with no link, and never
steals an employee already claimed by another account.

Usage: uv run python scripts/link_users_to_employees.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

import app.modules.employees.models  # noqa: F401  (FK target registration)
from app.db.session import SessionLocal
from app.modules.auth import service as auth_service
from app.modules.auth.models import User


def main() -> None:
    db = SessionLocal()
    try:
        before = db.scalars(select(User).where(User.employee_id.is_(None))).all()
        print(f"Unlinked accounts before: {len(before)}")

        linked = auth_service.backfill_employee_links(db)

        still_unlinked = db.scalars(select(User).where(User.employee_id.is_(None))).all()
        print(f"Linked this run: {linked}")
        if still_unlinked:
            print(
                f"Still unlinked ({len(still_unlinked)}) — no employee has a matching "
                "staff number, which is expected for system accounts:"
            )
            for user in still_unlinked:
                print(f"  - {user.staff_no}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
