"""add_unparsed_files_table

Revision ID: 32c7e675a295
Revises: 56ef54c7930e
Create Date: 2025-12-29 03:10:19.053854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32c7e675a295'
down_revision: Union[str, None] = '56ef54c7930e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'unparsed_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer()),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('bank_name', sa.String(100)),  # User-provided if auto-detection fails
        sa.Column('detection_attempted', sa.Boolean(), server_default='true'),
        sa.Column('detection_result', sa.JSON()),  # Store detection confidence scores
        sa.Column('status', sa.String(20), server_default='pending'),  # pending, parsed, failed
        sa.Column('error_message', sa.Text()),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime()),
    )
    op.create_index('idx_unparsed_files_user', 'unparsed_files', ['user_id'])
    op.create_index('idx_unparsed_files_status', 'unparsed_files', ['status'])


def downgrade() -> None:
    op.drop_index('idx_unparsed_files_status', 'unparsed_files')
    op.drop_index('idx_unparsed_files_user', 'unparsed_files')
    op.drop_table('unparsed_files')

