"""link users to employees

Revision ID: aaabf184ba1d
Revises: 4c4da7bb24be
Create Date: 2026-07-25 06:51:18.501808

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aaabf184ba1d'
down_revision: str | None = '4c4da7bb24be'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Note: the two index drops autogenerate detected here (employee_salaries,
    # position_rates) are the same known false positive seen throughout this
    # project's migration history (FK-owned index vs explicit index-name
    # quirk) — not a real schema change, so they're omitted.
    op.create_index(
        "uq_users_employee_id",
        "users",
        ["employee_id"],
        unique=True,
        postgresql_where=sa.text("employee_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_users_employee_id", table_name="users", postgresql_where=sa.text("employee_id IS NOT NULL")
    )
