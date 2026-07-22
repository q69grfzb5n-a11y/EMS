#!/usr/bin/env python3
"""Idempotent seed script. Usage: uv run python scripts/seed.py --core"""

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

# Not otherwise used here, but User.employee_id's ForeignKey("employees.id")
# needs the Employee class registered on the shared mapper registry before any
# flush touching `users` can resolve it — without this import, seeding a truly
# fresh database (no prior User row already flushed) fails with
# NoReferencedTableError. Masked for a long time by this project's live dev
# database already having the bootstrap admin row from long before this FK
# existed; caught by Phase 9's from-scratch prod-profile validation.
import app.modules.employees.models  # noqa: F401
from app.common.enums import RoleCode, TemplateVersionStatus
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import Role, User, UserRole
from app.modules.kpi_templates.models import KpiCriterion, KpiTemplate, KpiTemplateVersion
from app.modules.org.models import Department, Position, PositionRate

SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "db" / "seed_data"

ROLES: list[tuple[RoleCode, str, str]] = [
    (RoleCode.HR, "HR", "الموارد البشرية"),
    (RoleCode.ADMIN, "Admin", "مدير النظام"),
    (RoleCode.PMO, "PMO", "مكتب إدارة المشاريع"),
    (RoleCode.FACTORY_MANAGER, "Factory Manager", "مدير المصنع"),
    (RoleCode.DEPT_MANAGER, "Department Manager", "مدير القسم"),
    (RoleCode.REVIEWER, "Reviewer", "مقيّم"),
    (RoleCode.FINANCE, "Finance", "المالية"),
    (RoleCode.KEY_PERSON, "Key Person", "موظف رئيسي"),
    (RoleCode.EMPLOYEE, "Employee", "موظف"),
]

ADMIN_STAFF_NO = "0001"
ADMIN_DEFAULT_PASSWORD = "ChangeMe123!"
# Bootstrap only: the runtime API forbids anyone (including admin) from self-granting
# roles — HR is the only role allowed to call PUT /users/{id}/roles. Seeding this
# account with both roles directly in the DB is how the very first HR user gets
# created, bypassing that API-level rule on purpose for initial provisioning.
ADMIN_BOOTSTRAP_ROLES = [RoleCode.ADMIN, RoleCode.HR]


def seed_roles(db: Session) -> dict[str, Role]:
    roles_by_code: dict[str, Role] = {}
    for code, name_en, name_ar in ROLES:
        role = db.scalars(select(Role).where(Role.code == code.value)).first()
        if role is None:
            role = Role(code=code.value, name_en=name_en, name_ar=name_ar)
            db.add(role)
            db.flush()
            print(f"  + created role {code.value}")
        else:
            role.name_en = name_en
            role.name_ar = name_ar
        roles_by_code[code.value] = role
    db.commit()
    return roles_by_code


def seed_admin_user(db: Session, roles_by_code: dict[str, Role]) -> None:
    user = db.scalars(select(User).where(User.staff_no == ADMIN_STAFF_NO)).first()
    if user is None:
        user = User(
            staff_no=ADMIN_STAFF_NO,
            password_hash=hash_password(ADMIN_DEFAULT_PASSWORD),
            must_change_password=True,
            is_active=True,
        )
        db.add(user)
        db.flush()
        print(
            f"  + created admin user {ADMIN_STAFF_NO} (default password: {ADMIN_DEFAULT_PASSWORD})"
        )
    else:
        print(f"  = admin user {ADMIN_STAFF_NO} already exists, leaving password untouched")

    existing_role_ids = {ur.role_id for ur in user.user_roles}
    for code in ADMIN_BOOTSTRAP_ROLES:
        role = roles_by_code[code.value]
        if role.id not in existing_role_ids:
            db.add(UserRole(user_id=user.id, role_id=role.id, granted_by_user_id=None))
            print(f"  + granted {code.value} to {ADMIN_STAFF_NO}")
    db.commit()


# Flat rates predate the system; no real effective date is known, so they're seeded as open
# windows starting from a fixed epoch. Superseded once HR provides dated position_rates.
RATE_CARD_EPOCH = "2020-01-01"


def seed_departments(db: Session) -> None:
    data = json.loads((SEED_DATA_DIR / "departments.json").read_text(encoding="utf-8"))
    for row in data:
        dept = db.scalars(select(Department).where(Department.code == row["code"])).first()
        if dept is None:
            dept = Department(**row)
            db.add(dept)
            print(f"  + created department {row['code']}")
        else:
            dept.name_en = row["name_en"]
            dept.name_ar = row["name_ar"]
            dept.is_active = row["is_active"]
    db.commit()


def seed_positions(db: Session) -> None:
    data = json.loads((SEED_DATA_DIR / "positions.json").read_text(encoding="utf-8"))
    for row in data:
        position = db.scalars(select(Position).where(Position.code == row["code"])).first()
        if position is None:
            position = Position(
                code=row["code"],
                title_en=row["title_en"],
                title_ar=row["title_ar"],
                is_active=row["is_active"],
            )
            db.add(position)
            db.flush()
            print(f"  + created position {row['code']}")
        else:
            position.title_en = row["title_en"]
            position.title_ar = row["title_ar"]
            position.is_active = row["is_active"]

        rate = db.scalars(
            select(PositionRate).where(
                PositionRate.position_id == position.id,
                PositionRate.effective_to.is_(None),
            )
        ).first()
        flat_ref_amount = Decimal(str(row["flat_ref_amount"]))
        if rate is None:
            db.add(
                PositionRate(
                    position_id=position.id,
                    effective_from=RATE_CARD_EPOCH,
                    flat_ref_amount=flat_ref_amount,
                )
            )
            print(f"  + created open rate window for {row['code']} ({flat_ref_amount} SAR)")
        else:
            rate.flat_ref_amount = flat_ref_amount
    db.commit()


def seed_kpi_templates(db: Session) -> None:
    """Seeds the 4 real templates pre-activated (version 1, status=active) so
    positions can be assigned immediately. Active versions are otherwise
    immutable (enforced by the service layer) — re-running this only updates
    the template's own name_en/name_ar, never a version already made active."""
    data = json.loads((SEED_DATA_DIR / "kpi_templates.json").read_text(encoding="utf-8"))
    for row in data:
        template = db.scalars(select(KpiTemplate).where(KpiTemplate.code == row["code"])).first()
        if template is None:
            template = KpiTemplate(code=row["code"], name_en=row["name_en"], name_ar=row["name_ar"])
            db.add(template)
            db.flush()
            print(f"  + created template {row['code']}")
        else:
            template.name_en = row["name_en"]
            template.name_ar = row["name_ar"]

        has_version = db.scalars(
            select(KpiTemplateVersion).where(KpiTemplateVersion.template_id == template.id)
        ).first()
        if has_version is not None:
            continue

        version = KpiTemplateVersion(
            template_id=template.id, version_no=1, status=TemplateVersionStatus.ACTIVE.value
        )
        db.add(version)
        db.flush()
        for criterion in row["criteria"]:
            db.add(KpiCriterion(template_version_id=version.id, **criterion))
        print(f"  + created + activated v1 for {row['code']} ({len(row['criteria'])} criteria)")
    db.commit()


def seed_core() -> None:
    db = SessionLocal()
    try:
        print("Seeding roles...")
        roles_by_code = seed_roles(db)
        print("Seeding admin user...")
        seed_admin_user(db, roles_by_code)
        print("Seeding departments...")
        seed_departments(db)
        print("Seeding positions + flat rates...")
        seed_positions(db)
        print("Seeding KPI templates...")
        seed_kpi_templates(db)
        print("Core seed complete.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", action="store_true", help="Seed roles + admin user")
    args = parser.parse_args()

    if args.core:
        seed_core()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
