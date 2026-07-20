"""phase 3: kpi templates

Revision ID: c77cd59823ee
Revises: 1861e1738425
Create Date: 2026-07-19 17:50:27.734589

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c77cd59823ee'
down_revision: str | None = '1861e1738425'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('kpi_templates',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name_en', sa.String(length=150), nullable=False),
    sa.Column('name_ar', sa.String(length=150), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_kpi_templates'))
    )
    op.create_index(op.f('ix_kpi_templates_code'), 'kpi_templates', ['code'], unique=True)
    op.create_table('kpi_template_assignments',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('position_id', sa.BigInteger(), nullable=False),
    sa.Column('template_id', sa.BigInteger(), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('effective_to', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['position_id'], ['positions.id'], name=op.f('fk_kpi_template_assignments_position_id')),
    sa.ForeignKeyConstraint(['template_id'], ['kpi_templates.id'], name=op.f('fk_kpi_template_assignments_template_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_kpi_template_assignments'))
    )
    op.create_index(op.f('ix_kpi_template_assignments_position_id'), 'kpi_template_assignments', ['position_id'], unique=False)
    op.execute(
        """
        ALTER TABLE kpi_template_assignments
        ADD CONSTRAINT ck_kpi_template_assignments_no_overlap
        EXCLUDE USING gist (
            position_id WITH =,
            daterange(effective_from, effective_to, '[)') WITH &&
        )
        """
    )
    op.create_table('kpi_template_versions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('template_id', sa.BigInteger(), nullable=False),
    sa.Column('version_no', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['template_id'], ['kpi_templates.id'], name=op.f('fk_kpi_template_versions_template_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_kpi_template_versions')),
    sa.UniqueConstraint('template_id', 'version_no', name='uq_kpi_template_versions_version_no')
    )
    op.create_index('uq_kpi_template_versions_one_active', 'kpi_template_versions', ['template_id'], unique=True, postgresql_where=sa.text("status = 'active'"))
    op.create_table('kpi_criteria',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('template_version_id', sa.BigInteger(), nullable=False),
    sa.Column('name_en', sa.String(length=200), nullable=False),
    sa.Column('name_ar', sa.String(length=200), nullable=False),
    sa.Column('guidance_en', sa.Text(), nullable=True),
    sa.Column('guidance_ar', sa.Text(), nullable=True),
    sa.Column('max_marks', sa.SmallInteger(), nullable=False),
    sa.Column('input_mode', sa.String(length=20), nullable=False),
    sa.Column('allow_negative', sa.Boolean(), nullable=False),
    sa.Column('auto_source', sa.String(length=20), nullable=False),
    sa.Column('auto_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('sort_order', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('max_marks > 0', name=op.f('ck_kpi_criteria_max_marks_positive')),
    sa.ForeignKeyConstraint(['template_version_id'], ['kpi_template_versions.id'], name=op.f('fk_kpi_criteria_template_version_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_kpi_criteria'))
    )
    # NOTE: autogenerate also proposed dropping ix_employee_salaries_employee_id and
    # ix_position_rates_position_id — a false positive from a pre-existing drift
    # between those Phase 2 indexes and their ORM models (indexes exist in the DB,
    # just not declared via index=True on the model columns). Deliberately not
    # touched here; unrelated to Phase 3.


def downgrade() -> None:
    op.drop_table('kpi_criteria')
    op.drop_index('uq_kpi_template_versions_one_active', table_name='kpi_template_versions', postgresql_where=sa.text("status = 'active'"))
    op.drop_table('kpi_template_versions')
    op.execute('ALTER TABLE kpi_template_assignments DROP CONSTRAINT ck_kpi_template_assignments_no_overlap')
    op.drop_index(op.f('ix_kpi_template_assignments_position_id'), table_name='kpi_template_assignments')
    op.drop_table('kpi_template_assignments')
    op.drop_index(op.f('ix_kpi_templates_code'), table_name='kpi_templates')
    op.drop_table('kpi_templates')
