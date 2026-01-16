"""Rename persons to workspaces throughout the database.

Revision ID: 20260116_0100
Revises: 20260104_0100
Create Date: 2026-01-16 01:00:00.000000

This migration renames:
- Table: persons -> workspaces
- Column: person_id -> workspace_id in all tables
- All related indexes and foreign keys
"""
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260116_0100'
down_revision = '20260104_0100'
branch_labels = None
depends_on = None


# Tables with person_id foreign keys that need renaming
TABLES_WITH_PERSON_FK = [
    'transactions',
    'categories',
    'rules',
    'user_accounts',
    'chat_sessions',
    'chat_messages',
    'chat_contexts',
    'token_usage',
    'background_jobs',
    'recurring_occurrences',
    'unparsed_files',
    'reports',
    'insights',
    'recurring_groups',
]


def upgrade():
    """Rename persons table to workspaces and person_id columns to workspace_id."""
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Step 1: Drop all foreign key constraints referencing persons table
    for table in TABLES_WITH_PERSON_FK:
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            if 'person_id' in fk['constrained_columns'] and fk.get('name'):
                op.drop_constraint(fk['name'], table, type_='foreignkey')
    
    # Step 2: Drop indexes on person_id columns
    for table in TABLES_WITH_PERSON_FK:
        indexes = inspector.get_indexes(table)
        for idx in indexes:
            if 'person_id' in idx['column_names'] and idx.get('name'):
                op.drop_index(idx['name'], table_name=table)
    
    # Step 3: Drop persons table constraints and indexes
    # Drop unique constraint
    try:
        op.drop_constraint('uq_persons_user_name', 'persons', type_='unique')
    except Exception:
        pass  # May not exist
    
    # Drop index on user_id
    try:
        op.drop_index('ix_persons_user_id', table_name='persons')
    except Exception:
        pass  # May not exist
    
    # Step 4: Rename the persons table to workspaces
    op.rename_table('persons', 'workspaces')
    
    # Step 5: Rename person_id column to workspace_id in all tables
    for table in TABLES_WITH_PERSON_FK:
        op.alter_column(table, 'person_id', new_column_name='workspace_id')
    
    # Step 6: Recreate constraints and indexes on workspaces table
    op.create_index('ix_workspaces_user_id', 'workspaces', ['user_id'], unique=False)
    op.create_unique_constraint('uq_workspaces_user_name', 'workspaces', ['user_id', 'name'])
    
    # Step 7: Recreate foreign keys and indexes for workspace_id columns
    for table in TABLES_WITH_PERSON_FK:
        # Create foreign key with CASCADE
        op.create_foreign_key(
            f'fk_{table}_workspace_id',
            table,
            'workspaces',
            ['workspace_id'],
            ['id'],
            ondelete='CASCADE'
        )
        
        # Create index on workspace_id
        op.create_index(f'ix_{table}_workspace_id', table, ['workspace_id'], unique=False)
    
    # Step 8: Recreate special composite indexes
    # Transactions has a person_date composite index
    op.create_index('ix_transactions_workspace_date', 'transactions', ['workspace_id', 'date'], unique=False)


def downgrade():
    """Rename workspaces table back to persons and workspace_id columns back to person_id."""
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Step 1: Drop all foreign key constraints referencing workspaces table
    for table in TABLES_WITH_PERSON_FK:
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            if 'workspace_id' in fk['constrained_columns'] and fk.get('name'):
                op.drop_constraint(fk['name'], table, type_='foreignkey')
    
    # Step 2: Drop indexes on workspace_id columns (including composite)
    try:
        op.drop_index('ix_transactions_workspace_date', table_name='transactions')
    except Exception:
        pass
    
    for table in TABLES_WITH_PERSON_FK:
        indexes = inspector.get_indexes(table)
        for idx in indexes:
            if 'workspace_id' in idx['column_names'] and idx.get('name'):
                op.drop_index(idx['name'], table_name=table)
    
    # Step 3: Drop workspaces table constraints and indexes
    try:
        op.drop_constraint('uq_workspaces_user_name', 'workspaces', type_='unique')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_workspaces_user_id', table_name='workspaces')
    except Exception:
        pass
    
    # Step 4: Rename the workspaces table back to persons
    op.rename_table('workspaces', 'persons')
    
    # Step 5: Rename workspace_id column back to person_id in all tables
    for table in TABLES_WITH_PERSON_FK:
        op.alter_column(table, 'workspace_id', new_column_name='person_id')
    
    # Step 6: Recreate constraints and indexes on persons table
    op.create_index('ix_persons_user_id', 'persons', ['user_id'], unique=False)
    op.create_unique_constraint('uq_persons_user_name', 'persons', ['user_id', 'name'])
    
    # Step 7: Recreate foreign keys and indexes for person_id columns
    for table in TABLES_WITH_PERSON_FK:
        op.create_foreign_key(
            f'fk_{table}_person_id',
            table,
            'persons',
            ['person_id'],
            ['id'],
            ondelete='CASCADE'
        )
        op.create_index(f'ix_{table}_person_id', table, ['person_id'], unique=False)
    
    # Step 8: Recreate special composite indexes
    op.create_index('ix_transactions_person_date', 'transactions', ['person_id', 'date'], unique=False)
