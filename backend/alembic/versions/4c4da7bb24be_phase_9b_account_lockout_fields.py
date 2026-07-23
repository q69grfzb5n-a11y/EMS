"""phase 9b account lockout fields

Revision ID: 4c4da7bb24be
Revises: d7c84014bc07
Create Date: 2026-07-23 08:56:20.185798

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c4da7bb24be'
down_revision: str | None = 'd7c84014bc07'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Note: the two index drops autogenerate detected here (employee_salaries,
    # position_rates) are the same known false positive seen in every prior
    # phase's migration (FK-owned index vs explicit index-name quirk) — not a
    # real schema change, so they're omitted rather than applied.
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
