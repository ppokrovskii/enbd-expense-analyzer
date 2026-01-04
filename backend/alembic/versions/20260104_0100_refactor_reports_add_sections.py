"""refactor reports table and add report_sections

Revision ID: 20260104_0100
Revises: 20260103_1500
Create Date: 2026-01-04 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260104_0100'
down_revision = '20260103_1500'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old indexes (if they exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('reports')]
    
    if 'ix_reports_status' in indexes:
        op.drop_index('ix_reports_status', table_name='reports')
    
    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('reports')]
    
    # Drop old columns from reports table (if they exist)
    columns_to_drop = ['report_type', 'report_format', 'status', 'period_start', 
                       'period_end', 'file_path', 'file_size', 'metadata_json', 
                       'error_message', 'completed_at']
    for col in columns_to_drop:
        if col in columns:
            op.drop_column('reports', col)
    
    # Rename title to name (if title exists and name doesn't)
    if 'title' in columns and 'name' not in columns:
        op.alter_column('reports', 'title', new_column_name='name')
    
    # Add updated_at column (if it doesn't exist)
    if 'updated_at' not in columns:
        op.add_column('reports', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Create report_sections table (if it doesn't exist)
    tables = inspector.get_table_names()
    if 'report_sections' not in tables:
        op.create_table(
            'report_sections',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('section_type', sa.String(50), nullable=False),
            sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('custom_title', sa.String(255), nullable=True),
            sa.Column('filters_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('content_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
            sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for report_sections
        op.create_index('ix_report_sections_report_id', 'report_sections', ['report_id'], unique=False)
        op.create_index('ix_report_sections_position', 'report_sections', ['position'], unique=False)


def downgrade() -> None:
    # Drop report_sections table and indexes
    op.drop_index('ix_report_sections_position', table_name='report_sections')
    op.drop_index('ix_report_sections_report_id', table_name='report_sections')
    op.drop_table('report_sections')
    
    # Remove updated_at from reports
    op.drop_column('reports', 'updated_at')
    
    # Rename name back to title
    op.alter_column('reports', 'name', new_column_name='title')
    
    # Re-add old columns to reports table
    op.add_column('reports', sa.Column('report_type', sa.String(), nullable=True))
    op.add_column('reports', sa.Column('report_format', sa.String(), nullable=True))
    op.add_column('reports', sa.Column('status', sa.String(), nullable=True))
    op.add_column('reports', sa.Column('period_start', sa.Date(), nullable=True))
    op.add_column('reports', sa.Column('period_end', sa.Date(), nullable=True))
    op.add_column('reports', sa.Column('file_path', sa.String(), nullable=True))
    op.add_column('reports', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('reports', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('reports', sa.Column('completed_at', sa.DateTime(), nullable=True))
    
    # Re-create old index
    op.create_index('ix_reports_status', 'reports', ['status'], unique=False)

