"""Add crm_sync_log and csv_import_jobs tables

Revision ID: 003_integrations
Revises: 002_scoring_attribution
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision    = '003_integrations'
down_revision = '002_scoring_attribution'
branch_labels = None
depends_on    = None

def upgrade():
    # ── crm_sync_log ─────────────────────────────────────────
    op.create_table('crm_sync_log',
        sa.Column('id',           sa.String(),  primary_key=True),
        sa.Column('crm',          sa.String(),  nullable=False),  # salesforce / hubspot
        sa.Column('direction',    sa.String(),  nullable=False),  # push / pull
        sa.Column('status',       sa.String(),  nullable=False),  # success / error
        sa.Column('records_synced', sa.Integer(), server_default='0'),
        sa.Column('errors',       JSONB,        server_default='[]'),
        sa.Column('started_at',   sa.DateTime()),
        sa.Column('finished_at',  sa.DateTime()),
        sa.Column('created_at',   sa.DateTime(), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_crm_log_crm',    'crm_sync_log', ['crm'])
    op.create_index('ix_crm_log_status', 'crm_sync_log', ['status'])

    # ── csv_import_jobs ──────────────────────────────────────
    op.create_table('csv_import_jobs',
        sa.Column('id',              sa.String(),  primary_key=True),
        sa.Column('filename',        sa.String()),
        sa.Column('status',          sa.String(),  server_default="'pending'"),
        sa.Column('total_rows',      sa.Integer(), server_default='0'),
        sa.Column('inserted',        sa.Integer(), server_default='0'),
        sa.Column('updated',         sa.Integer(), server_default='0'),
        sa.Column('invalid_rows',    sa.Integer(), server_default='0'),
        sa.Column('duplicates_in_csv', sa.Integer(), server_default='0'),
        sa.Column('duplicates_in_db',  sa.Integer(), server_default='0'),
        sa.Column('errors',          JSONB,        server_default='[]'),
        sa.Column('uploaded_by',     sa.String()),
        sa.Column('on_conflict',     sa.String(),  server_default="'update'"),
        sa.Column('created_at',      sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('completed_at',    sa.DateTime()),
    )

    # ── marketo_migration_log ────────────────────────────────
    op.create_table('marketo_migration_log',
        sa.Column('id',              sa.String(),  primary_key=True),
        sa.Column('status',          sa.String(),  server_default="'pending'"),
        sa.Column('contacts_imported', sa.Integer(), server_default='0'),
        sa.Column('templates_imported',sa.Integer(), server_default='0'),
        sa.Column('errors',          JSONB,        server_default='[]'),
        sa.Column('started_at',      sa.DateTime()),
        sa.Column('completed_at',    sa.DateTime()),
        sa.Column('created_at',      sa.DateTime(), server_default=sa.text('NOW()')),
    )

def downgrade():
    op.drop_table('marketo_migration_log')
    op.drop_table('csv_import_jobs')
    op.drop_table('crm_sync_log')
