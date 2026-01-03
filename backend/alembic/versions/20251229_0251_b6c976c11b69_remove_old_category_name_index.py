"""remove_old_category_name_index

Revision ID: b6c976c11b69
Revises: 6d2ffbe5a38d
Create Date: 2025-12-29 02:51:18.137468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c976c11b69'
down_revision: Union[str, None] = '6d2ffbe5a38d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove old unique index on just 'name' column
    # We now have idx_categories_user_name (user_id, name) which is the correct unique constraint
    op.drop_index('ix_categories_name', 'categories')


def downgrade() -> None:
    op.create_index('ix_categories_name', 'categories', ['name'], unique=True)

