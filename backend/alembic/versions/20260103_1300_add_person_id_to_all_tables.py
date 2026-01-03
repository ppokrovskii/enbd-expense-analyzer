"""Add person_id to remaining tables for complete data isolation.

Revision ID: 20260103_1300
Revises: 20260103_1200
Create Date: 2026-01-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260103_1300'
down_revision = '20260103_1200'
branch_labels = None
depends_on = None


def upgrade():
    """Add person_id to chat, jobs, recurring_occurrences, unparsed_files tables.
    Note: reports, insights, recurring_groups already have person_id from earlier."""
    
    # Chat sessions
    op.add_column('chat_sessions', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_chat_sessions_person_id', 'chat_sessions', 'persons', ['person_id'], ['id'])
    op.create_index('ix_chat_sessions_person_id', 'chat_sessions', ['person_id'], unique=False)
    
    # Chat messages
    op.add_column('chat_messages', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_chat_messages_person_id', 'chat_messages', 'persons', ['person_id'], ['id'])
    op.create_index('ix_chat_messages_person_id', 'chat_messages', ['person_id'], unique=False)
    
    # Chat contexts
    op.add_column('chat_contexts', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_chat_contexts_person_id', 'chat_contexts', 'persons', ['person_id'], ['id'])
    op.create_index('ix_chat_contexts_person_id', 'chat_contexts', ['person_id'], unique=False)
    
    # Token usage
    op.add_column('token_usage', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_token_usage_person_id', 'token_usage', 'persons', ['person_id'], ['id'])
    op.create_index('ix_token_usage_person_id', 'token_usage', ['person_id'], unique=False)
    
    # Background jobs
    op.add_column('background_jobs', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_background_jobs_person_id', 'background_jobs', 'persons', ['person_id'], ['id'])
    op.create_index('ix_background_jobs_person_id', 'background_jobs', ['person_id'], unique=False)
    
    # Recurring occurrences
    op.add_column('recurring_occurrences', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_recurring_occurrences_person_id', 'recurring_occurrences', 'persons', ['person_id'], ['id'])
    op.create_index('ix_recurring_occurrences_person_id', 'recurring_occurrences', ['person_id'], unique=False)
    
    # Unparsed files
    op.add_column('unparsed_files', sa.Column('person_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_unparsed_files_person_id', 'unparsed_files', 'persons', ['person_id'], ['id'])
    op.create_index('ix_unparsed_files_person_id', 'unparsed_files', ['person_id'], unique=False)


def downgrade():
    """Remove person_id from tables added in this migration."""
    # Unparsed files
    op.drop_index('ix_unparsed_files_person_id', table_name='unparsed_files')
    op.drop_constraint('fk_unparsed_files_person_id', 'unparsed_files', type_='foreignkey')
    op.drop_column('unparsed_files', 'person_id')
    
    # Recurring occurrences
    op.drop_index('ix_recurring_occurrences_person_id', table_name='recurring_occurrences')
    op.drop_constraint('fk_recurring_occurrences_person_id', 'recurring_occurrences', type_='foreignkey')
    op.drop_column('recurring_occurrences', 'person_id')
    
    # Background jobs
    op.drop_index('ix_background_jobs_person_id', table_name='background_jobs')
    op.drop_constraint('fk_background_jobs_person_id', 'background_jobs', type_='foreignkey')
    op.drop_column('background_jobs', 'person_id')
    
    # Token usage
    op.drop_index('ix_token_usage_person_id', table_name='token_usage')
    op.drop_constraint('fk_token_usage_person_id', 'token_usage', type_='foreignkey')
    op.drop_column('token_usage', 'person_id')
    
    # Chat contexts
    op.drop_index('ix_chat_contexts_person_id', table_name='chat_contexts')
    op.drop_constraint('fk_chat_contexts_person_id', 'chat_contexts', type_='foreignkey')
    op.drop_column('chat_contexts', 'person_id')
    
    # Chat messages
    op.drop_index('ix_chat_messages_person_id', table_name='chat_messages')
    op.drop_constraint('fk_chat_messages_person_id', 'chat_messages', type_='foreignkey')
    op.drop_column('chat_messages', 'person_id')
    
    # Chat sessions
    op.drop_index('ix_chat_sessions_person_id', table_name='chat_sessions')
    op.drop_constraint('fk_chat_sessions_person_id', 'chat_sessions', type_='foreignkey')
    op.drop_column('chat_sessions', 'person_id')

