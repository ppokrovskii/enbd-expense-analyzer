"""Update categories unique constraint to include person_id.

Revision ID: 20260103_1400
Revises: 20260103_1300
Create Date: 2026-01-03 14:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '20260103_1400'
down_revision = '20260103_1300'
branch_labels = None
depends_on = None


def upgrade():
    """Update unique constraint to include person_id."""
    # Drop the old unique constraint
    op.drop_index('idx_categories_user_name', table_name='categories')
    
    # Create new unique constraint that includes person_id
    # Note: We use coalesce for person_id since it can be NULL
    op.create_index(
        'idx_categories_user_person_name',
        'categories',
        ['user_id', 'person_id', 'name'],
        unique=True
    )


def downgrade():
    """Revert to old unique constraint."""
    op.drop_index('idx_categories_user_person_name', table_name='categories')
    op.create_index('idx_categories_user_name', 'categories', ['user_id', 'name'], unique=True)

