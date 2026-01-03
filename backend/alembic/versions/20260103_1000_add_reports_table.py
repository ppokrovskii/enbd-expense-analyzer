"""add reports table

Revision ID: 20260103_1000
Revises: 20260103_0900
Create Date: 2026-01-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260103_1000'
down_revision = '20260103_0900'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('report_type', sa.String(), nullable=False),
        sa.Column('report_format', sa.String(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reports_user_id', 'reports', ['user_id'], unique=False)
    op.create_index('ix_reports_created_at', 'reports', ['created_at'], unique=False)
    op.create_index('ix_reports_status', 'reports', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reports_status', table_name='reports')
    op.drop_index('ix_reports_created_at', table_name='reports')
    op.drop_index('ix_reports_user_id', table_name='reports')
    op.drop_table('reports')

