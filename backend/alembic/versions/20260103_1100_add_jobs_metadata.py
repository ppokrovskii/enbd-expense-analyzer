"""add job_params column to background_jobs

Revision ID: 20260103_1100
Revises: 20260103_1000
Create Date: 2026-01-03 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260103_1100'
down_revision = '20260103_1000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add job_params column to background_jobs for storing job-specific parameters
    op.add_column('background_jobs', sa.Column('job_params', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('background_jobs', 'job_params')

