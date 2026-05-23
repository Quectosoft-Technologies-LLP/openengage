"""Add scoring_rules and campaign_attributions tables

Revision ID: 002_scoring_attribution
Revises: 001_initial
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '002_scoring_attribution'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # ── scoring_rules (configurable, patent-safe additive rules) ─
    op.create_table('scoring_rules',
        sa.Column('id',             sa.String(),  primary_key=True),
        sa.Column('activity_type',  sa.String(),  nullable=False, unique=True),
        sa.Column('points',         sa.Integer(), nullable=False),
        sa.Column('description',    sa.String()),
        sa.Column('is_active',      sa.Boolean(), server_default='true'),
        sa.Column('created_at',     sa.DateTime(),server_default=sa.text('NOW()')),
        sa.Column('updated_at',     sa.DateTime(),server_default=sa.text('NOW()')),
    )
    # Seed default rules
    op.execute("""
        INSERT INTO scoring_rules (id, activity_type, points, description) VALUES
        (gen_random_uuid()::text, 'email_opened',          5,  'Opened an email'),
        (gen_random_uuid()::text, 'email_clicked',        10,  'Clicked a link in email'),
        (gen_random_uuid()::text, 'form_submitted',       25,  'Submitted any form'),
        (gen_random_uuid()::text, 'page_visited',          2,  'Visited any tracked page'),
        (gen_random_uuid()::text, 'pricing_page_visited', 15,  'Visited pricing page'),
        (gen_random_uuid()::text, 'demo_requested',       50,  'Requested a demo'),
        (gen_random_uuid()::text, 'webinar_attended',     30,  'Attended a webinar'),
        (gen_random_uuid()::text, 'content_downloaded',   20,  'Downloaded a content asset'),
        (gen_random_uuid()::text, 'email_unsubscribed',  -10,  'Unsubscribed from emails'),
        (gen_random_uuid()::text, 'spam_reported',       -50,  'Marked email as spam')
    """)

    # ── campaign_attributions (linear multi-touch, patent-safe) ──
    op.create_table('campaign_attributions',
        sa.Column('id',               sa.String(), primary_key=True),
        sa.Column('contact_id',       sa.String(), sa.ForeignKey('contacts.id', ondelete='CASCADE')),
        sa.Column('campaign_id',      sa.String(), sa.ForeignKey('campaigns.id', ondelete='CASCADE')),
        sa.Column('touch_sequence',   sa.Integer(), nullable=False),  # 1=first, 2=second, etc.
        sa.Column('attribution_model',sa.String(), server_default="'linear'"),  # linear/first/last
        sa.Column('credit_amount',    sa.Float(),  nullable=False),   # equal share (linear)
        sa.Column('conversion_value', sa.Float(),  server_default='0.0'),
        sa.Column('touched_at',       sa.DateTime()),
        sa.Column('converted_at',     sa.DateTime()),
        sa.Column('created_at',       sa.DateTime(), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_attr_contact',  'campaign_attributions', ['contact_id'])
    op.create_index('ix_attr_campaign', 'campaign_attributions', ['campaign_id'])

    # ── ab_test_variants ──────────────────────────────────────
    op.create_table('ab_test_variants',
        sa.Column('id',            sa.String(),  primary_key=True),
        sa.Column('campaign_id',   sa.String(),  sa.ForeignKey('campaigns.id', ondelete='CASCADE')),
        sa.Column('variant_name',  sa.String(),  nullable=False),  # A, B, C
        sa.Column('subject_line',  sa.String()),
        sa.Column('html_body',     sa.Text()),
        sa.Column('sent_count',    sa.Integer(), server_default='0'),
        sa.Column('open_count',    sa.Integer(), server_default='0'),
        sa.Column('click_count',   sa.Integer(), server_default='0'),
        sa.Column('open_rate',     sa.Float(),   server_default='0.0'),
        sa.Column('is_winner',     sa.Boolean(), server_default='false'),
        sa.Column('created_at',    sa.DateTime(),server_default=sa.text('NOW()')),
    )

def downgrade():
    op.drop_table('ab_test_variants')
    op.drop_table('campaign_attributions')
    op.drop_table('scoring_rules')
