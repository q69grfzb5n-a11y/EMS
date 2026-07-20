"""phase 5: approvals and evaluations

Revision ID: 0bd3259e2bd4
Revises: 754b32c3632c
Create Date: 2026-07-19 23:27:30.925405

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0bd3259e2bd4'
down_revision: str | None = '754b32c3632c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('approval_actions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.BigInteger(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('from_status', sa.String(length=50), nullable=False),
    sa.Column('to_status', sa.String(length=50), nullable=False),
    sa.Column('actor_user_id', sa.BigInteger(), nullable=False),
    sa.Column('actor_role', sa.String(length=50), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_approval_actions_actor_user_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_approval_actions'))
    )
    op.create_index('ix_approval_actions_entity', 'approval_actions', ['entity_type', 'entity_id'], unique=False)
    op.create_table('evaluations',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('employee_id', sa.BigInteger(), nullable=False),
    sa.Column('period_id', sa.BigInteger(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('template_version_id', sa.BigInteger(), nullable=False),
    sa.Column('owner_user_id', sa.BigInteger(), nullable=False),
    sa.Column('activities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('score_pct', sa.Numeric(precision=6, scale=4), nullable=True),
    sa.Column('grade', sa.String(length=1), nullable=True),
    sa.Column('row_version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], name=op.f('fk_evaluations_employee_id')),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], name=op.f('fk_evaluations_owner_user_id')),
    sa.ForeignKeyConstraint(['period_id'], ['incentive_periods.id'], name=op.f('fk_evaluations_period_id')),
    sa.ForeignKeyConstraint(['template_version_id'], ['kpi_template_versions.id'], name=op.f('fk_evaluations_template_version_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluations')),
    sa.UniqueConstraint('employee_id', 'period_id', 'kind', name='uq_evaluations_employee_period_kind')
    )
    op.create_index(op.f('ix_evaluations_employee_id'), 'evaluations', ['employee_id'], unique=False)
    op.create_index(op.f('ix_evaluations_period_id'), 'evaluations', ['period_id'], unique=False)
    op.create_table('notifications',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.BigInteger(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_table('evaluation_scores',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('evaluation_id', sa.BigInteger(), nullable=False),
    sa.Column('criterion_id', sa.BigInteger(), nullable=False),
    sa.Column('raw_input', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('awarded_marks', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('auto_suggested_marks', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['criterion_id'], ['kpi_criteria.id'], name=op.f('fk_evaluation_scores_criterion_id')),
    sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], name=op.f('fk_evaluation_scores_evaluation_id')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluation_scores')),
    sa.UniqueConstraint('evaluation_id', 'criterion_id', name='uq_evaluation_scores_eval_criterion')
    )
    op.create_index(op.f('ix_evaluation_scores_evaluation_id'), 'evaluation_scores', ['evaluation_id'], unique=False)
    # NOTE: autogenerate also proposed dropping ix_employee_salaries_employee_id and
    # ix_position_rates_position_id — the same pre-existing Phase 2 index/ORM drift
    # noted in the Phase 3/4 migrations. Deliberately not touched here either.


def downgrade() -> None:
    op.drop_index(op.f('ix_evaluation_scores_evaluation_id'), table_name='evaluation_scores')
    op.drop_table('evaluation_scores')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_evaluations_period_id'), table_name='evaluations')
    op.drop_index(op.f('ix_evaluations_employee_id'), table_name='evaluations')
    op.drop_table('evaluations')
    op.drop_index('ix_approval_actions_entity', table_name='approval_actions')
    op.drop_table('approval_actions')
