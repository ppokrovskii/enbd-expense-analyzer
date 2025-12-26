"""Initial schema with transactions, categories, and llm_cache

Revision ID: 965c026746cf
Revises: 
Create Date: 2025-12-26 13:08:58.686917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '965c026746cf'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('account', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('debit_credit', sa.String(length=10), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('balance', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('merchant', sa.String(length=200), nullable=True),
        sa.Column('amount_signed', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('week_start', sa.Date(), nullable=True),
        sa.Column('month', sa.String(length=7), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('transaction_hash', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_date'), 'transactions', ['date'], unique=False)
    op.create_index(op.f('ix_transactions_merchant'), 'transactions', ['merchant'], unique=False)
    op.create_index(op.f('ix_transactions_category'), 'transactions', ['category'], unique=False)
    op.create_index(op.f('ix_transactions_transaction_hash'), 'transactions', ['transaction_hash'], unique=True)
    op.create_index('idx_date_category', 'transactions', ['date', 'category'], unique=False)
    op.create_index('idx_merchant_category', 'transactions', ['merchant', 'category'], unique=False)
    
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('keywords', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_id'), 'categories', ['id'], unique=False)
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=True)
    
    # Create llm_cache table
    op.create_table(
        'llm_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_cache_id'), 'llm_cache', ['id'], unique=False)
    op.create_index(op.f('ix_llm_cache_merchant'), 'llm_cache', ['merchant'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_llm_cache_merchant'), table_name='llm_cache')
    op.drop_index(op.f('ix_llm_cache_id'), table_name='llm_cache')
    op.drop_table('llm_cache')
    op.drop_index(op.f('ix_categories_name'), table_name='categories')
    op.drop_index(op.f('ix_categories_id'), table_name='categories')
    op.drop_table('categories')
    op.drop_index('idx_merchant_category', table_name='transactions')
    op.drop_index('idx_date_category', table_name='transactions')
    op.drop_index(op.f('ix_transactions_transaction_hash'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_category'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_merchant'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_date'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')

