"""Add person_id to transactions table for person-based data isolation.

Revision ID: 20260103_1200
Revises: 20260103_1100
Create Date: 2026-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260103_1200'
down_revision = '20260103_1100'
branch_labels = None
depends_on = None


def upgrade():
    """Add person_id column to transactions table."""
    # Add person_id column (nullable initially for existing data)
    op.add_column('transactions', sa.Column('person_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_transactions_person_id',
        'transactions',
        'persons',
        ['person_id'],
        ['id']
    )
    
    # Create index for faster lookups
    op.create_index('ix_transactions_person_id', 'transactions', ['person_id'], unique=False)
    
    # Create composite index for person + date queries
    op.create_index('ix_transactions_person_date', 'transactions', ['person_id', 'date'], unique=False)
    
    # Also add person_id to categories and rules tables
    op.add_column('categories', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_categories_person_id', 'categories', 'persons', ['person_id'], ['id'])
    op.create_index('ix_categories_person_id', 'categories', ['person_id'], unique=False)
    
    op.add_column('rules', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_rules_person_id', 'rules', 'persons', ['person_id'], ['id'])
    op.create_index('ix_rules_person_id', 'rules', ['person_id'], unique=False)
    
    # Add person_id to user_accounts
    op.add_column('user_accounts', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_user_accounts_person_id', 'user_accounts', 'persons', ['person_id'], ['id'])


def downgrade():
    """Remove person_id column from transactions table."""
    op.drop_constraint('fk_user_accounts_person_id', 'user_accounts', type_='foreignkey')
    op.drop_column('user_accounts', 'person_id')
    
    op.drop_index('ix_rules_person_id', table_name='rules')
    op.drop_constraint('fk_rules_person_id', 'rules', type_='foreignkey')
    op.drop_column('rules', 'person_id')
    
    op.drop_index('ix_categories_person_id', table_name='categories')
    op.drop_constraint('fk_categories_person_id', 'categories', type_='foreignkey')
    op.drop_column('categories', 'person_id')
    
    op.drop_index('ix_transactions_person_date', table_name='transactions')
    op.drop_index('ix_transactions_person_id', table_name='transactions')
    op.drop_constraint('fk_transactions_person_id', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'person_id')

