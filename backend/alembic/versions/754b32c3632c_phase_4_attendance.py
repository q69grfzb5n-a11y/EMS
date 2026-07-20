"""phase 4: attendance

Revision ID: 754b32c3632c
Revises: c77cd59823ee
Create Date: 2026-07-19 22:48:41.284476

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '754b32c3632c'
down_revision: str | None = 'c77cd59823ee'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('incentive_periods',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('year', sa.SmallInteger(), nullable=False),
    sa.Column('month', sa.SmallInteger(), nullable=False),
    sa.Column('target_pool', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('actual_pool', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_incentive_periods')),
    sa.UniqueConstraint('year', 'month', name='uq_incentive_periods_year_month')
    )
    op.create_table('attendance_imports',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('period_id', sa.BigInteger(), nullable=False),
    sa.Column('file_sha256', sa.String(length=64), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('uploaded_by_user_id', sa.BigInteger(), nullable=False),
    sa.Column('row_count', sa.SmallInteger(), nullable=False),
    sa.Column('error_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['period_id'], ['incentive_periods.id'], name=op.f('fk_attendance_imports_period_id')),
    sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], name=op.f('fk_attendance_imports_uploaded_by_user_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attendance_imports')),
    sa.UniqueConstraint('period_id', 'file_sha256', name='uq_attendance_imports_period_sha256')
    )
    op.create_index(op.f('ix_attendance_imports_period_id'), 'attendance_imports', ['period_id'], unique=False)
    op.create_table('attendance_zero_flags',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('employee_id', sa.BigInteger(), nullable=False),
    sa.Column('period_from_id', sa.BigInteger(), nullable=False),
    sa.Column('period_to_id', sa.BigInteger(), nullable=False),
    sa.Column('total_leave_absence_days', sa.SmallInteger(), nullable=False),
    sa.Column('allowance_days', sa.SmallInteger(), nullable=False),
    sa.Column('is_overridden', sa.Boolean(), nullable=False),
    sa.Column('override_reason', sa.Text(), nullable=True),
    sa.Column('overridden_by_user_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], name=op.f('fk_attendance_zero_flags_employee_id')),
    sa.ForeignKeyConstraint(['overridden_by_user_id'], ['users.id'], name=op.f('fk_attendance_zero_flags_overridden_by_user_id')),
    sa.ForeignKeyConstraint(['period_from_id'], ['incentive_periods.id'], name=op.f('fk_attendance_zero_flags_period_from_id')),
    sa.ForeignKeyConstraint(['period_to_id'], ['incentive_periods.id'], name=op.f('fk_attendance_zero_flags_period_to_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attendance_zero_flags'))
    )
    op.create_index(op.f('ix_attendance_zero_flags_employee_id'), 'attendance_zero_flags', ['employee_id'], unique=False)
    op.create_table('attendance_records',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('period_id', sa.BigInteger(), nullable=False),
    sa.Column('employee_id', sa.BigInteger(), nullable=False),
    sa.Column('import_id', sa.BigInteger(), nullable=False),
    sa.Column('present', sa.SmallInteger(), nullable=False),
    sa.Column('off_days', sa.SmallInteger(), nullable=False),
    sa.Column('absent', sa.SmallInteger(), nullable=False),
    sa.Column('leave', sa.SmallInteger(), nullable=False),
    sa.Column('public_holiday', sa.SmallInteger(), nullable=False),
    sa.Column('deduct_min', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('over_time', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('approved', sa.SmallInteger(), nullable=False),
    sa.Column('pending_approval', sa.SmallInteger(), nullable=False),
    sa.Column('submitted', sa.SmallInteger(), nullable=False),
    sa.Column('approved_over_time', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], name=op.f('fk_attendance_records_employee_id')),
    sa.ForeignKeyConstraint(['import_id'], ['attendance_imports.id'], name=op.f('fk_attendance_records_import_id')),
    sa.ForeignKeyConstraint(['period_id'], ['incentive_periods.id'], name=op.f('fk_attendance_records_period_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attendance_records')),
    sa.UniqueConstraint('period_id', 'employee_id', name='uq_attendance_records_period_employee')
    )
    op.create_index(op.f('ix_attendance_records_employee_id'), 'attendance_records', ['employee_id'], unique=False)
    op.create_index(op.f('ix_attendance_records_period_id'), 'attendance_records', ['period_id'], unique=False)
    # NOTE: autogenerate also proposed dropping ix_employee_salaries_employee_id and
    # ix_position_rates_position_id — the same pre-existing Phase 2 index/ORM drift
    # noted in the Phase 3 migration. Deliberately not touched here either.


def downgrade() -> None:
    op.drop_index(op.f('ix_attendance_records_period_id'), table_name='attendance_records')
    op.drop_index(op.f('ix_attendance_records_employee_id'), table_name='attendance_records')
    op.drop_table('attendance_records')
    op.drop_index(op.f('ix_attendance_zero_flags_employee_id'), table_name='attendance_zero_flags')
    op.drop_table('attendance_zero_flags')
    op.drop_index(op.f('ix_attendance_imports_period_id'), table_name='attendance_imports')
    op.drop_table('attendance_imports')
    op.drop_table('incentive_periods')
