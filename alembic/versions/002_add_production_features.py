"""Add MFA, KYC, Webhook, Refund, Dispute tables

Revision ID: 002_add_production_features
Revises: 001_initial_schema
Create Date: 2025-01-XX

This migration adds tables for production features:
- user_mfa: Multi-factor authentication settings
- kyc_verifications: KYC verification records
- kyc_documents: KYC document uploads
- webhook_endpoints: Merchant webhook configurations
- webhook_deliveries: Webhook delivery attempts
- refunds: Refund requests
- chargebacks: Chargeback records
- disputes: Transaction disputes
- dispute_evidence: Evidence files for disputes
- dispute_comments: Comments on disputes
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_add_production_features'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all production feature tables."""
    
    # ====================================================================
    # MFA Table
    # ====================================================================
    op.create_table(
        'user_mfa',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('totp_secret', sa.String(length=64), nullable=True),
        sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('backup_codes_hash', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_user_mfa_id', 'user_mfa', ['id'])
    op.create_index('ix_user_mfa_user_id', 'user_mfa', ['user_id'], unique=True)

    # ====================================================================
    # KYC Tables
    # ====================================================================
    op.create_table(
        'kyc_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='not_started'),
        sa.Column('legal_first_name', sa.String(length=100), nullable=True),
        sa.Column('legal_last_name', sa.String(length=100), nullable=True),
        sa.Column('date_of_birth', sa.String(length=10), nullable=True),
        sa.Column('nationality', sa.String(length=2), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('tax_id', sa.String(length=50), nullable=True),
        sa.Column('tax_id_type', sa.String(length=20), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('sanctions_checked_at', sa.DateTime(), nullable=True),
        sa.Column('sanctions_clear', sa.Boolean(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
    )
    op.create_index('ix_kyc_verifications_id', 'kyc_verifications', ['id'])
    op.create_index('ix_kyc_verifications_user_id', 'kyc_verifications', ['user_id'])
    op.create_index('ix_kyc_verifications_status', 'kyc_verifications', ['status'])

    op.create_table(
        'kyc_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kyc_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=30), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=50), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.Column('extracted_data', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['kyc_id'], ['kyc_verifications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
    )
    op.create_index('ix_kyc_documents_id', 'kyc_documents', ['id'])
    op.create_index('ix_kyc_documents_kyc_id', 'kyc_documents', ['kyc_id'])

    # ====================================================================
    # Webhook Tables
    # ====================================================================
    op.create_table(
        'webhook_endpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('secret_key', sa.String(length=64), nullable=False),
        sa.Column('events', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_webhook_endpoints_id', 'webhook_endpoints', ['id'])
    op.create_index('ix_webhook_endpoints_merchant_id', 'webhook_endpoints', ['merchant_id'])

    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endpoint_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['endpoint_id'], ['webhook_endpoints.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index('ix_webhook_deliveries_id', 'webhook_deliveries', ['id'])
    op.create_index('ix_webhook_deliveries_endpoint_id', 'webhook_deliveries', ['endpoint_id'])
    op.create_index('ix_webhook_deliveries_event_type', 'webhook_deliveries', ['event_type'])
    op.create_index('ix_webhook_deliveries_status', 'webhook_deliveries', ['status'])

    # ====================================================================
    # Refund & Chargeback Tables
    # ====================================================================
    op.create_table(
        'refunds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('refund_type', sa.String(length=20), nullable=False, server_default='full'),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('processed_by', sa.Integer(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('reference_id', sa.String(length=64), nullable=True),
        sa.Column('extra_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['payment_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id']),
        sa.UniqueConstraint('reference_id'),
    )
    op.create_index('ix_refunds_id', 'refunds', ['id'])
    op.create_index('ix_refunds_payment_id', 'refunds', ['payment_id'])
    op.create_index('ix_refunds_status', 'refunds', ['status'])

    op.create_table(
        'chargebacks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('merchant_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('reason_code', sa.String(length=20), nullable=False),
        sa.Column('reason_description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='received'),
        sa.Column('evidence_due_by', sa.DateTime(), nullable=True),
        sa.Column('evidence_submitted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('evidence_details', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('fee_amount', sa.Numeric(8, 2), nullable=True),
        sa.Column('recovered_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('bank_reference', sa.String(length=100), nullable=True),
        sa.Column('network_case_id', sa.String(length=100), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['payment_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id']),
    )
    op.create_index('ix_chargebacks_id', 'chargebacks', ['id'])
    op.create_index('ix_chargebacks_payment_id', 'chargebacks', ['payment_id'])
    op.create_index('ix_chargebacks_status', 'chargebacks', ['status'])

    # ====================================================================
    # Dispute Tables
    # ====================================================================
    op.create_table(
        'disputes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('merchant_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='opened'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('response_due_by', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_type', sa.String(length=30), nullable=True),
        sa.Column('resolution_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('case_number', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['payment_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id']),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id']),
        sa.UniqueConstraint('case_number'),
    )
    op.create_index('ix_disputes_id', 'disputes', ['id'])
    op.create_index('ix_disputes_payment_id', 'disputes', ['payment_id'])
    op.create_index('ix_disputes_user_id', 'disputes', ['user_id'])
    op.create_index('ix_disputes_status', 'disputes', ['status'])
    op.create_index('ix_disputes_case_number', 'disputes', ['case_number'])

    op.create_table(
        'dispute_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispute_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('uploader_type', sa.String(length=20), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dispute_id'], ['disputes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_dispute_evidence_id', 'dispute_evidence', ['id'])
    op.create_index('ix_dispute_evidence_dispute_id', 'dispute_evidence', ['dispute_id'])

    op.create_table(
        'dispute_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispute_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=True),
        sa.Column('author_type', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dispute_id'], ['disputes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_dispute_comments_id', 'dispute_comments', ['id'])
    op.create_index('ix_dispute_comments_dispute_id', 'dispute_comments', ['dispute_id'])


def downgrade() -> None:
    """Drop all production feature tables."""
    op.drop_table('dispute_comments')
    op.drop_table('dispute_evidence')
    op.drop_table('disputes')
    op.drop_table('chargebacks')
    op.drop_table('refunds')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_endpoints')
    op.drop_table('kyc_documents')
    op.drop_table('kyc_verifications')
    op.drop_table('user_mfa')
