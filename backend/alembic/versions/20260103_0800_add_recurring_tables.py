"""add recurring tables

Revision ID: 20260103_0800
Revises: 20260103_0600
Create Date: 2026-01-03 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260103_0800'
down_revision = '20260103_0600'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create recurring_groups table
    op.create_table(
        'recurring_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('pattern_name', sa.String(), nullable=False),
        sa.Column('merchant', sa.String(), nullable=False),
        sa.Column('estimated_amount', sa.Float(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('occurrences_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_seen_date', sa.Date(), nullable=True),
        sa.Column('next_expected_date', sa.Date(), nullable=True),
        sa.Column('forgotten', sa.Boolean(), default=False),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recurring_groups_user_id', 'recurring_groups', ['user_id'], unique=False)
    op.create_index('ix_recurring_groups_merchant', 'recurring_groups', ['merchant'], unique=False)
    
    # Create recurring_occurrences table
    op.create_table(
        'recurring_occurrences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recurring_group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['recurring_group_id'], ['recurring_groups.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recurring_occurrences_group_id', 'recurring_occurrences', ['recurring_group_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_recurring_occurrences_group_id', table_name='recurring_occurrences')
    op.drop_table('recurring_occurrences')
    op.drop_index('ix_recurring_groups_merchant', table_name='recurring_groups')
    op.drop_index('ix_recurring_groups_user_id', table_name='recurring_groups')
    op.drop_table('recurring_groups')

