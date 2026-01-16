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
from sqlalchemy import text


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
    conn = op.get_bind()
    
    # Step 1: Drop all foreign key constraints referencing persons table
    for table in TABLES_WITH_PERSON_FK:
        fk_name = f'fk_{table}_person_id'
        conn.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {fk_name}'))
    
    # Step 2: Drop indexes on person_id columns
    for table in TABLES_WITH_PERSON_FK:
        idx_name = f'ix_{table}_person_id'
        conn.execute(text(f'DROP INDEX IF EXISTS {idx_name}'))
    
    # Drop the composite index on transactions
    conn.execute(text('DROP INDEX IF EXISTS ix_transactions_person_date'))
    
    # Step 3: Drop persons table constraints and indexes
    conn.execute(text('DROP INDEX IF EXISTS ix_persons_user_id'))
    conn.execute(text('ALTER TABLE persons DROP CONSTRAINT IF EXISTS uq_persons_user_name'))
    
    # Step 4: Rename the persons table to workspaces
    conn.execute(text('ALTER TABLE persons RENAME TO workspaces'))
    
    # Step 5: Rename person_id column to workspace_id in all tables
    for table in TABLES_WITH_PERSON_FK:
        conn.execute(text(f'ALTER TABLE {table} RENAME COLUMN person_id TO workspace_id'))
    
    # Step 6: Recreate constraints and indexes on workspaces table
    conn.execute(text('CREATE INDEX ix_workspaces_user_id ON workspaces (user_id)'))
    conn.execute(text('ALTER TABLE workspaces ADD CONSTRAINT uq_workspaces_user_name UNIQUE (user_id, name)'))
    
    # Step 7: Recreate foreign keys and indexes for workspace_id columns
    for table in TABLES_WITH_PERSON_FK:
        fk_name = f'fk_{table}_workspace_id'
        idx_name = f'ix_{table}_workspace_id'
        conn.execute(text(f'''
            ALTER TABLE {table} 
            ADD CONSTRAINT {fk_name} 
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        '''))
        conn.execute(text(f'CREATE INDEX {idx_name} ON {table} (workspace_id)'))
    
    # Step 8: Recreate special composite indexes
    conn.execute(text('CREATE INDEX ix_transactions_workspace_date ON transactions (workspace_id, date)'))


def downgrade():
    """Rename workspaces table back to persons and workspace_id columns back to person_id."""
    conn = op.get_bind()
    
    # Step 1: Drop all foreign key constraints referencing workspaces table
    for table in TABLES_WITH_PERSON_FK:
        fk_name = f'fk_{table}_workspace_id'
        conn.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {fk_name}'))
    
    # Step 2: Drop indexes on workspace_id columns
    conn.execute(text('DROP INDEX IF EXISTS ix_transactions_workspace_date'))
    for table in TABLES_WITH_PERSON_FK:
        idx_name = f'ix_{table}_workspace_id'
        conn.execute(text(f'DROP INDEX IF EXISTS {idx_name}'))
    
    # Step 3: Drop workspaces table constraints and indexes
    conn.execute(text('DROP INDEX IF EXISTS ix_workspaces_user_id'))
    conn.execute(text('ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS uq_workspaces_user_name'))
    
    # Step 4: Rename the workspaces table back to persons
    conn.execute(text('ALTER TABLE workspaces RENAME TO persons'))
    
    # Step 5: Rename workspace_id column back to person_id in all tables
    for table in TABLES_WITH_PERSON_FK:
        conn.execute(text(f'ALTER TABLE {table} RENAME COLUMN workspace_id TO person_id'))
    
    # Step 6: Recreate constraints and indexes on persons table
    conn.execute(text('CREATE INDEX ix_persons_user_id ON persons (user_id)'))
    conn.execute(text('ALTER TABLE persons ADD CONSTRAINT uq_persons_user_name UNIQUE (user_id, name)'))
    
    # Step 7: Recreate foreign keys and indexes for person_id columns
    for table in TABLES_WITH_PERSON_FK:
        fk_name = f'fk_{table}_person_id'
        idx_name = f'ix_{table}_person_id'
        conn.execute(text(f'''
            ALTER TABLE {table} 
            ADD CONSTRAINT {fk_name} 
            FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
        '''))
        conn.execute(text(f'CREATE INDEX {idx_name} ON {table} (person_id)'))
    
    # Step 8: Recreate special composite indexes
    conn.execute(text('CREATE INDEX ix_transactions_person_date ON transactions (person_id, date)'))
