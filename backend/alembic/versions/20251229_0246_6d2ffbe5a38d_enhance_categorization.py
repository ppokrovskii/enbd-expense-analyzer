"""enhance_categorization

Revision ID: 6d2ffbe5a38d
Revises: b789f9bda8fb
Create Date: 2025-12-29 02:46:28.781070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d2ffbe5a38d'
down_revision: Union[str, None] = 'b789f9bda8fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add search_text column to transactions
    op.add_column('transactions', sa.Column('search_text', sa.Text()))
    
    # Populate search_text with concatenated details and description
    op.execute("""
        UPDATE transactions 
        SET search_text = CONCAT(
            COALESCE(details, ''), 
            ' ', 
            COALESCE(description, '')
        )
    """)
    
    # Create GIN index for full-text search using pg_trgm
    # Note: Requires pg_trgm extension to be enabled
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX idx_transactions_search_text 
        ON transactions 
        USING gin(search_text gin_trgm_ops)
    """)
    
    # Add new columns to categories
    op.add_column('categories', sa.Column('color', sa.String(20)))
    op.add_column('categories', sa.Column('exclude_keywords', sa.JSON()))
    op.add_column('categories', sa.Column('match_both_fields', sa.Boolean(), server_default='true'))


def downgrade() -> None:
    op.drop_index('idx_transactions_search_text', 'transactions')
    op.drop_column('transactions', 'search_text')
    op.drop_column('categories', 'match_both_fields')
    op.drop_column('categories', 'exclude_keywords')
    op.drop_column('categories', 'color')

