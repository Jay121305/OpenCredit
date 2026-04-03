"""Add dashboard features - financial records and expanded roles

Revision ID: 003_add_dashboard_features
Revises: 002_add_production_features
Create Date: 2026-04-03

This migration adds:
- updated_at and deactivated_at columns to users table
- financial_records table for dashboard record tracking
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '003_add_dashboard_features'
down_revision: Union[str, None] = '002_add_production_features'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dashboard features."""
    
    # ====================================================================
    # Update Users Table - Add new columns for enhanced role management
    # ====================================================================
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('deactivated_at', sa.DateTime(), nullable=True))
    
    # ====================================================================
    # Financial Records Table
    # ====================================================================
    op.create_table(
        'financial_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('record_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Primary indexes
    op.create_index('ix_financial_records_id', 'financial_records', ['id'])
    op.create_index('ix_financial_records_user_id', 'financial_records', ['user_id'])
    op.create_index('ix_financial_records_type', 'financial_records', ['type'])
    op.create_index('ix_financial_records_category', 'financial_records', ['category'])
    op.create_index('ix_financial_records_record_date', 'financial_records', ['record_date'])
    
    # Composite indexes for common query patterns
    op.create_index('ix_records_user_date', 'financial_records', ['user_id', 'record_date'])
    op.create_index('ix_records_user_type', 'financial_records', ['user_id', 'type'])
    op.create_index('ix_records_user_category', 'financial_records', ['user_id', 'category'])
    op.create_index('ix_records_user_active', 'financial_records', ['user_id', 'is_deleted', 'status'])


def downgrade() -> None:
    """Remove dashboard features."""
    # Drop financial_records table and indexes
    op.drop_index('ix_records_user_active', 'financial_records')
    op.drop_index('ix_records_user_category', 'financial_records')
    op.drop_index('ix_records_user_type', 'financial_records')
    op.drop_index('ix_records_user_date', 'financial_records')
    op.drop_index('ix_financial_records_record_date', 'financial_records')
    op.drop_index('ix_financial_records_category', 'financial_records')
    op.drop_index('ix_financial_records_type', 'financial_records')
    op.drop_index('ix_financial_records_user_id', 'financial_records')
    op.drop_index('ix_financial_records_id', 'financial_records')
    op.drop_table('financial_records')
    
    # Remove columns from users
    op.drop_column('users', 'deactivated_at')
    op.drop_column('users', 'updated_at')
