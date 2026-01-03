"""Add multi-tenant support and chat tables

Revision ID: 20251228_0751
Revises: 965c026746cf
Create Date: 2025-12-28 07:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251228_0751'
down_revision: Union[str, None] = '965c026746cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id to existing tables
    op.add_column('transactions', sa.Column('user_id', sa.String(length=50), server_default='default_user', nullable=False))
    op.add_column('categories', sa.Column('user_id', sa.String(length=50), server_default='default_user', nullable=False))
    op.add_column('llm_cache', sa.Column('user_id', sa.String(length=50), server_default='default_user', nullable=False))
    
    # Create indexes for user_id on existing tables
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'], unique=False)
    op.create_index('ix_categories_user_id', 'categories', ['user_id'], unique=False)
    op.create_index('ix_llm_cache_user_id', 'llm_cache', ['user_id'], unique=False)
    
    # Create composite indexes for better query performance
    op.create_index('idx_transactions_user_date', 'transactions', ['user_id', 'date'], unique=False)
    op.create_index('idx_transactions_user_category', 'transactions', ['user_id', 'category'], unique=False)
    op.create_index('idx_transactions_user_merchant', 'transactions', ['user_id', 'merchant'], unique=False)
    op.create_index('idx_categories_user_name', 'categories', ['user_id', 'name'], unique=True)
    op.create_index('idx_llm_cache_user_merchant', 'llm_cache', ['user_id', 'merchant'], unique=True)
    
    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_sessions_id', 'chat_sessions', ['id'], unique=False)
    op.create_index('idx_chat_sessions_user_updated', 'chat_sessions', ['user_id', 'updated_at'], unique=False)
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE')
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'], unique=False)
    op.create_index('idx_chat_messages_session_created', 'chat_messages', ['session_id', 'created_at'], unique=False)
    
    # Create chat_contexts table
    op.create_table(
        'chat_contexts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_filters', sa.JSON(), nullable=True),
        sa.Column('transaction_count', sa.Integer(), nullable=True),
        sa.Column('transaction_summary', sa.JSON(), nullable=True),
        sa.Column('include_categories', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_id', name='uq_chat_contexts_session_id')
    )
    op.create_index('ix_chat_contexts_id', 'chat_contexts', ['id'], unique=False)
    op.create_index('ix_chat_contexts_session_id', 'chat_contexts', ['session_id'], unique=True)
    
    # Create token_usage table
    op.create_table(
        'token_usage',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.String(length=50), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='SET NULL')
    )
    op.create_index('ix_token_usage_id', 'token_usage', ['id'], unique=False)
    op.create_index('idx_token_usage_user_created', 'token_usage', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop token_usage table
    op.drop_index('idx_token_usage_user_created', table_name='token_usage')
    op.drop_index('ix_token_usage_id', table_name='token_usage')
    op.drop_table('token_usage')
    
    # Drop chat_contexts table
    op.drop_index('ix_chat_contexts_session_id', table_name='chat_contexts')
    op.drop_index('ix_chat_contexts_id', table_name='chat_contexts')
    op.drop_table('chat_contexts')
    
    # Drop chat_messages table
    op.drop_index('idx_chat_messages_session_created', table_name='chat_messages')
    op.drop_index('ix_chat_messages_id', table_name='chat_messages')
    op.drop_table('chat_messages')
    
    # Drop chat_sessions table
    op.drop_index('idx_chat_sessions_user_updated', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_id', table_name='chat_sessions')
    op.drop_table('chat_sessions')
    
    # Remove composite indexes from existing tables
    op.drop_index('idx_llm_cache_user_merchant', table_name='llm_cache')
    op.drop_index('idx_categories_user_name', table_name='categories')
    op.drop_index('idx_transactions_user_merchant', table_name='transactions')
    op.drop_index('idx_transactions_user_category', table_name='transactions')
    op.drop_index('idx_transactions_user_date', table_name='transactions')
    
    # Remove user_id indexes from existing tables
    op.drop_index('ix_llm_cache_user_id', table_name='llm_cache')
    op.drop_index('ix_categories_user_id', table_name='categories')
    op.drop_index('ix_transactions_user_id', table_name='transactions')
    
    # Remove user_id columns from existing tables
    op.drop_column('llm_cache', 'user_id')
    op.drop_column('categories', 'user_id')
    op.drop_column('transactions', 'user_id')

