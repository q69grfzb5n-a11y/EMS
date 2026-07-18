#!/usr/bin/env python3
"""Idempotent seed script. Usage: uv run python scripts/seed.py --core"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import RoleCode
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import Role, User, UserRole

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
            f"  + created admin user {ADMIN_STAFF_NO} "
            f"(default password: {ADMIN_DEFAULT_PASSWORD})"
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


def seed_core() -> None:
    db = SessionLocal()
    try:
        print("Seeding roles...")
        roles_by_code = seed_roles(db)
        print("Seeding admin user...")
        seed_admin_user(db, roles_by_code)
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
