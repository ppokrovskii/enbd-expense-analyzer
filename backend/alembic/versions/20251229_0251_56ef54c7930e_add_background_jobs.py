"""add_background_jobs

Revision ID: 56ef54c7930e
Revises: b6c976c11b69
Create Date: 2025-12-29 02:51:49.752198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '56ef54c7930e'
down_revision: Union[str, None] = 'b6c976c11b69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID as string
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('progress', sa.Integer(), server_default='0'),
        sa.Column('total_items', sa.Integer()),
        sa.Column('processed_items', sa.Integer(), server_default='0'),
        sa.Column('result', sa.JSON()),
        sa.Column('error', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
    )
    op.create_index('idx_jobs_user_status', 'background_jobs', ['user_id', 'status'])


def downgrade() -> None:
    op.drop_index('idx_jobs_user_status', 'background_jobs')
    op.drop_table('background_jobs')

