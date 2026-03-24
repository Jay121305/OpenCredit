"""Initial schema - create all tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-03-23

This migration creates the initial database schema for OpenCredit:
- users: User accounts with authentication
- credit_accounts: Credit lines linked to users
- merchants: Merchant accounts with API keys
- transactions: Payment transaction records
- ledger_blocks: Hash-chained transaction ledger
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Credit accounts table
    op.create_table(
        'credit_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credit_limit', sa.Float(), nullable=False, server_default='5000.0'),
        sa.Column('available_credit', sa.Float(), nullable=False, server_default='5000.0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_credit_accounts_id', 'credit_accounts', ['id'])
    op.create_index('ix_credit_accounts_user_id', 'credit_accounts', ['user_id'], unique=True)

    # Merchants table
    op.create_table(
        'merchants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('api_key_hash', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_merchants_id', 'merchants', ['id'])
    op.create_index('ix_merchants_api_key_hash', 'merchants', ['api_key_hash'], unique=True)

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('geo', sa.String(length=2), nullable=False),
        sa.Column('status', sa.Enum('approved', 'rejected', 'flagged', name='transactionstatus'), nullable=False),
        sa.Column('fraud_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('ix_transactions_idempotency_key', 'transactions', ['idempotency_key'], unique=True)
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])

    # Ledger blocks table
    op.create_table(
        'ledger_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=False),
        sa.Column('block_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ledger_blocks_id', 'ledger_blocks', ['id'])
    op.create_index('ix_ledger_blocks_block_hash', 'ledger_blocks', ['block_hash'], unique=True)


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('ledger_blocks')
    op.drop_table('transactions')
    op.drop_table('merchants')
    op.drop_table('credit_accounts')
    op.drop_table('users')
