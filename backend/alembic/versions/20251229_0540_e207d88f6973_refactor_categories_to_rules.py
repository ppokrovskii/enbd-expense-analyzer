"""refactor_categories_to_rules

Revision ID: e207d88f6973
Revises: 32c7e675a295
Create Date: 2025-12-29 05:40:56.403065

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json


# revision identifiers, used by Alembic.
revision: str = 'e207d88f6973'
down_revision: Union[str, None] = '32c7e675a295'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create rules table
    op.create_table(
        'rules',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False, index=True),
        sa.Column('keywords', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('exclude_keywords', postgresql.JSON(astext_type=sa.Text()), server_default='[]'),
        sa.Column('priority', sa.Integer(), default=0, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Create indexes
    op.create_index('idx_rules_category', 'rules', ['category_id'])
    op.create_index('idx_rules_user', 'rules', ['user_id'])
    
    # Migrate existing data: categories.keywords -> rules
    connection = op.get_bind()
    
    # Get all categories that have keywords
    result = connection.execute(sa.text(
        "SELECT id, user_id, keywords, exclude_keywords FROM categories WHERE keywords IS NOT NULL AND keywords::text != '[]'"
    ))
    
    categories_with_keywords = result.fetchall()
    
    for cat in categories_with_keywords:
        cat_id, user_id, keywords, exclude_keywords = cat
        
        # Parse JSON if it's a string
        if isinstance(keywords, str):
            keywords = json.loads(keywords)
        if exclude_keywords and isinstance(exclude_keywords, str):
            exclude_keywords = json.loads(exclude_keywords)
        elif not exclude_keywords:
            exclude_keywords = []
        
        # Only create rule if there are keywords
        if keywords and len(keywords) > 0:
            connection.execute(
                sa.text(
                    "INSERT INTO rules (category_id, user_id, keywords, exclude_keywords, priority) "
                    "VALUES (:cat_id, :user_id, :keywords, :exclude_keywords, 0)"
                ),
                {
                    "cat_id": cat_id,
                    "user_id": user_id,
                    "keywords": json.dumps(keywords),
                    "exclude_keywords": json.dumps(exclude_keywords)
                }
            )
    
    # Drop old columns from categories
    op.drop_column('categories', 'keywords')
    op.drop_column('categories', 'exclude_keywords')
    op.drop_column('categories', 'match_both_fields')


def downgrade() -> None:
    # Add back the old columns
    op.add_column('categories', sa.Column('keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('categories', sa.Column('exclude_keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('categories', sa.Column('match_both_fields', sa.Boolean(), server_default='true'))
    
    # Migrate rules back to categories
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT category_id, keywords, exclude_keywords FROM rules"))
    
    rules = result.fetchall()
    for rule in rules:
        category_id, keywords, exclude_keywords = rule
        
        # Parse JSON if needed
        if isinstance(keywords, str):
            keywords = json.loads(keywords)
        if exclude_keywords and isinstance(exclude_keywords, str):
            exclude_keywords = json.loads(exclude_keywords)
        
        connection.execute(
            sa.text(
                "UPDATE categories SET keywords = :keywords, exclude_keywords = :exclude_keywords "
                "WHERE id = :category_id"
            ),
            {
                "keywords": json.dumps(keywords),
                "exclude_keywords": json.dumps(exclude_keywords) if exclude_keywords else '[]',
                "category_id": category_id
            }
        )
    
    # Drop rules table
    op.drop_index('idx_rules_user', table_name='rules')
    op.drop_index('idx_rules_category', table_name='rules')
    op.drop_table('rules')

