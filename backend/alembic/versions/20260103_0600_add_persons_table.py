"""Add persons table for multi-person management.

Revision ID: 20260103_0600
Revises: e207d88f6973
Create Date: 2026-01-03 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260103_0600'
down_revision = 'e207d88f6973'
branch_labels = None
depends_on = None


def upgrade():
    """Create persons table."""
    op.create_table(
        'persons',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on user_id for faster lookups
    op.create_index(op.f('ix_persons_user_id'), 'persons', ['user_id'], unique=False)
    
    # Create unique constraint on (user_id, name) to prevent duplicate names per user
    op.create_unique_constraint('uq_persons_user_name', 'persons', ['user_id', 'name'])


def downgrade():
    """Drop persons table."""
    op.drop_constraint('uq_persons_user_name', 'persons', type_='unique')
    op.drop_index(op.f('ix_persons_user_id'), table_name='persons')
    op.drop_table('persons')

