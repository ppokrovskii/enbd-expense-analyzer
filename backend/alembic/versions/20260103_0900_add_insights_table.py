"""add insights table

Revision ID: 20260103_0900
Revises: 20260103_0800
Create Date: 2026-01-03 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260103_0900'
down_revision = '20260103_0800'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create insights table
    op.create_table(
        'insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('insight_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('data_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('is_dismissed', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_insights_user_id', 'insights', ['user_id'], unique=False)
    op.create_index('ix_insights_created_at', 'insights', ['created_at'], unique=False)
    op.create_index('ix_insights_type_severity', 'insights', ['insight_type', 'severity'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_insights_type_severity', table_name='insights')
    op.drop_index('ix_insights_created_at', table_name='insights')
    op.drop_index('ix_insights_user_id', table_name='insights')
    op.drop_table('insights')

