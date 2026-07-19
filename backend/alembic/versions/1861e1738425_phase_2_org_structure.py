"""phase 2: org structure (departments, positions, position_rates, employees,
employee_salaries, evaluation_assignments)

Revision ID: 1861e1738425
Revises: 4fda2a9bd0fa
Create Date: 2026-07-19 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1861e1738425'
down_revision: str | None = '4fda2a9bd0fa'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # btree_gist: lets the position_rates/employee_salaries EXCLUDE constraints combine a
    # plain equality column (position_id / employee_id) with a GiST range-overlap check.
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    # pg_trgm: fuzzy/substring Arabic+English name search on employees.
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    op.create_table(
        'departments',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('name_ar', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_departments')),
    )
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)

    op.create_table(
        'positions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('title_en', sa.String(length=100), nullable=False),
        sa.Column('title_ar', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_positions')),
    )
    op.create_index(op.f('ix_positions_code'), 'positions', ['code'], unique=True)

    op.create_table(
        'position_rates',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('position_id', sa.BigInteger(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('incentive_pct', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('flat_ref_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            'incentive_pct IS NOT NULL OR flat_ref_amount IS NOT NULL',
            name=op.f('ck_position_rates_rate_present'),
        ),
        sa.ForeignKeyConstraint(
            ['position_id'], ['positions.id'], name=op.f('fk_position_rates_position_id')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_position_rates')),
    )
    op.create_index(
        op.f('ix_position_rates_position_id'), 'position_rates', ['position_id'], unique=False
    )
    op.execute(
        """
        ALTER TABLE position_rates
        ADD CONSTRAINT ck_position_rates_no_overlap
        EXCLUDE USING gist (
            position_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&
        )
        """
    )

    op.create_table(
        'employees',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('staff_no', sa.String(length=20), nullable=False),
        sa.Column('full_name_ar', sa.String(length=200), nullable=False),
        sa.Column('full_name_en', sa.String(length=200), nullable=True),
        sa.Column('department_id', sa.BigInteger(), nullable=False),
        sa.Column('position_id', sa.BigInteger(), nullable=False),
        sa.Column('contract_position_title', sa.String(length=200), nullable=True),
        sa.Column('contract_years', sa.SmallInteger(), nullable=True),
        sa.Column('contract_start_date', sa.Date(), nullable=True),
        sa.Column('employment_status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['department_id'], ['departments.id'], name=op.f('fk_employees_department_id')
        ),
        sa.ForeignKeyConstraint(
            ['position_id'], ['positions.id'], name=op.f('fk_employees_position_id')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_employees')),
    )
    op.create_index(op.f('ix_employees_staff_no'), 'employees', ['staff_no'], unique=True)
    op.create_index(
        'ix_employees_full_name_ar_trgm',
        'employees',
        ['full_name_ar'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'full_name_ar': 'gin_trgm_ops'},
    )
    op.create_index(
        'ix_employees_full_name_en_trgm',
        'employees',
        ['full_name_en'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'full_name_en': 'gin_trgm_ops'},
    )

    op.create_table(
        'employee_salaries',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('employee_id', sa.BigInteger(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('base_salary', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['employee_id'], ['employees.id'], name=op.f('fk_employee_salaries_employee_id')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_employee_salaries')),
    )
    op.create_index(
        op.f('ix_employee_salaries_employee_id'),
        'employee_salaries',
        ['employee_id'],
        unique=False,
    )
    op.execute(
        """
        ALTER TABLE employee_salaries
        ADD CONSTRAINT ck_employee_salaries_no_overlap
        EXCLUDE USING gist (
            employee_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&
        )
        """
    )

    op.create_table(
        'evaluation_assignments',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('employee_id', sa.BigInteger(), nullable=False),
        sa.Column('reviewer_user_id', sa.BigInteger(), nullable=False),
        sa.Column('assigned_by_user_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['assigned_by_user_id'],
            ['users.id'],
            name=op.f('fk_evaluation_assignments_assigned_by_user_id'),
        ),
        sa.ForeignKeyConstraint(
            ['employee_id'], ['employees.id'], name=op.f('fk_evaluation_assignments_employee_id')
        ),
        sa.ForeignKeyConstraint(
            ['reviewer_user_id'],
            ['users.id'],
            name=op.f('fk_evaluation_assignments_reviewer_user_id'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluation_assignments')),
        sa.UniqueConstraint('employee_id', name=op.f('uq_evaluation_assignments_employee_id')),
    )

    op.create_foreign_key(
        op.f('fk_users_employee_id'), 'users', 'employees', ['employee_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_users_employee_id'), 'users', type_='foreignkey')

    op.drop_table('evaluation_assignments')

    op.execute('ALTER TABLE employee_salaries DROP CONSTRAINT ck_employee_salaries_no_overlap')
    op.drop_index(op.f('ix_employee_salaries_employee_id'), table_name='employee_salaries')
    op.drop_table('employee_salaries')

    op.drop_index(
        'ix_employees_full_name_en_trgm', table_name='employees', postgresql_using='gin'
    )
    op.drop_index(
        'ix_employees_full_name_ar_trgm', table_name='employees', postgresql_using='gin'
    )
    op.drop_index(op.f('ix_employees_staff_no'), table_name='employees')
    op.drop_table('employees')

    op.execute('ALTER TABLE position_rates DROP CONSTRAINT ck_position_rates_no_overlap')
    op.drop_index(op.f('ix_position_rates_position_id'), table_name='position_rates')
    op.drop_table('position_rates')

    op.drop_index(op.f('ix_positions_code'), table_name='positions')
    op.drop_table('positions')

    op.drop_index(op.f('ix_departments_code'), table_name='departments')
    op.drop_table('departments')
