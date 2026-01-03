"""add_user_accounts

Revision ID: b789f9bda8fb
Revises: 20251228_0751
Create Date: 2025-12-29 02:42:43.435935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b789f9bda8fb'
down_revision: Union[str, None] = '20251228_0751'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_accounts table
    op.create_table(
        'user_accounts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('account_name', sa.String(100), nullable=False),
        sa.Column('account_number', sa.String(50)),
        sa.Column('account_number_masked', sa.String(50)),
        sa.Column('bank', sa.String(50), nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_user_accounts', 'user_accounts', ['user_id'])
    op.create_unique_constraint('uq_user_account_name', 'user_accounts', ['user_id', 'account_name'])


def downgrade() -> None:
    op.drop_constraint('uq_user_account_name', 'user_accounts', type_='unique')
    op.drop_index('idx_user_accounts', 'user_accounts')
    op.drop_table('user_accounts')

