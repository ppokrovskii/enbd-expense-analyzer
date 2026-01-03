"""Add CASCADE DELETE to person_id foreign keys.

Revision ID: 20260103_1500
Revises: 20260103_1400
Create Date: 2026-01-03 15:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260103_1500'
down_revision = '20260103_1400'
branch_labels = None
depends_on = None


# Tables with person_id foreign keys that need CASCADE
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
    """Update foreign keys to include ON DELETE CASCADE."""
    connection = op.get_bind()
    inspector = inspect(connection)
    
    for table in TABLES_WITH_PERSON_FK:
        # Get current foreign keys for the table
        fks = inspector.get_foreign_keys(table)
        
        # Find the person_id foreign key
        person_fk = None
        for fk in fks:
            if 'person_id' in fk['constrained_columns']:
                person_fk = fk
                break
        
        if person_fk and person_fk.get('name'):
            # Drop the existing constraint by its actual name
            op.drop_constraint(person_fk['name'], table, type_='foreignkey')
            
            # Recreate with CASCADE
            op.create_foreign_key(
                f'fk_{table}_person_id',
                table,
                'persons',
                ['person_id'],
                ['id'],
                ondelete='CASCADE'
            )


def downgrade():
    """Remove CASCADE from foreign keys."""
    connection = op.get_bind()
    inspector = inspect(connection)
    
    for table in TABLES_WITH_PERSON_FK:
        fks = inspector.get_foreign_keys(table)
        person_fk = None
        for fk in fks:
            if 'person_id' in fk['constrained_columns']:
                person_fk = fk
                break
        
        if person_fk and person_fk.get('name'):
            op.drop_constraint(person_fk['name'], table, type_='foreignkey')
            op.create_foreign_key(
                f'fk_{table}_person_id',
                table,
                'persons',
                ['person_id'],
                ['id']
            )

