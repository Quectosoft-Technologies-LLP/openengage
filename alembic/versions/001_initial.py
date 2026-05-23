"""Initial schema — contacts, campaigns, segments, email_templates, activities, ai_suggestions

Revision ID: 001_initial
Revises: 
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # ── contacts ──────────────────────────────────────────────
    op.create_table('contacts',
        sa.Column('id',             sa.String(),   primary_key=True),
        sa.Column('email',          sa.String(),   nullable=False, unique=True),
        sa.Column('first_name',     sa.String()),
        sa.Column('last_name',      sa.String()),
        sa.Column('company',        sa.String()),
        sa.Column('industry',       sa.String()),
        sa.Column('job_title',      sa.String()),
        sa.Column('lead_score',     sa.Integer(),  server_default='0'),
        sa.Column('lifecycle_stage',sa.String(),   server_default="'lead'"),
        sa.Column('country',        sa.String()),
        sa.Column('city',           sa.String()),
        sa.Column('custom_fields',  JSONB,         server_default='{}'),
        sa.Column('created_at',     sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('last_active_at', sa.DateTime()),
    )
    op.create_index('ix_contacts_email',       'contacts', ['email'],       unique=True)
    op.create_index('ix_contacts_lead_score',  'contacts', ['lead_score'])
    op.create_index('ix_contacts_lifecycle',   'contacts', ['lifecycle_stage'])
    op.create_index('ix_contacts_industry',    'contacts', ['industry'])

    # ── segments ──────────────────────────────────────────────
    op.create_table('segments',
        sa.Column('id',           sa.String(), primary_key=True),
        sa.Column('name',         sa.String(), nullable=False),
        sa.Column('description',  sa.Text()),
        sa.Column('filters',      sa.Text(),   server_default="'[]'"),
        sa.Column('member_count', sa.Integer(),server_default='0'),
        sa.Column('created_at',   sa.DateTime(),server_default=sa.text('NOW()')),
    )

    # ── contact_segment_members ───────────────────────────────
    op.create_table('contact_segment_members',
        sa.Column('contact_id',  sa.String(), sa.ForeignKey('contacts.id', ondelete='CASCADE')),
        sa.Column('segment_id',  sa.String(), sa.ForeignKey('segments.id', ondelete='CASCADE')),
        sa.Column('added_at',    sa.DateTime(), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('contact_id', 'segment_id'),
    )
    op.create_index('ix_csm_segment', 'contact_segment_members', ['segment_id'])

    # ── campaigns ─────────────────────────────────────────────
    op.create_table('campaigns',
        sa.Column('id',                 sa.String(),  primary_key=True),
        sa.Column('name',               sa.String(),  nullable=False),
        sa.Column('type',               sa.String(),  server_default="'trigger'"),
        sa.Column('status',             sa.String(),  server_default="'draft'"),
        sa.Column('segment_id',         sa.String(),  sa.ForeignKey('segments.id')),
        sa.Column('filters',            sa.Text(),    server_default="'[]'"),
        sa.Column('flow_steps',         sa.Text(),    server_default="'[]'"),
        sa.Column('sent_count',         sa.Integer(), server_default='0'),
        sa.Column('open_count',         sa.Integer(), server_default='0'),
        sa.Column('click_count',        sa.Integer(), server_default='0'),
        sa.Column('conversion_count',   sa.Integer(), server_default='0'),
        sa.Column('revenue_attributed', sa.Float(),   server_default='0.0'),
        sa.Column('open_rate',          sa.Float(),   server_default='0.0'),
        sa.Column('click_rate',         sa.Float(),   server_default='0.0'),
        sa.Column('created_at',         sa.DateTime(),server_default=sa.text('NOW()')),
        sa.Column('launched_at',        sa.DateTime()),
    )
    op.create_index('ix_campaigns_status',     'campaigns', ['status'])
    op.create_index('ix_campaigns_type',       'campaigns', ['type'])

    # ── contact_activities ────────────────────────────────────
    op.create_table('contact_activities',
        sa.Column('id',            sa.String(),  primary_key=True),
        sa.Column('contact_id',    sa.String(),  sa.ForeignKey('contacts.id', ondelete='CASCADE')),
        sa.Column('campaign_id',   sa.String(),  sa.ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('activity_type', sa.String(),  nullable=False),
        sa.Column('metadata',      JSONB,        server_default='{}'),
        sa.Column('created_at',    sa.DateTime(),server_default=sa.text('NOW()')),
    )
    op.create_index('ix_activities_contact',  'contact_activities', ['contact_id'])
    op.create_index('ix_activities_type',     'contact_activities', ['activity_type'])
    op.create_index('ix_activities_campaign', 'contact_activities', ['campaign_id'])

    # ── email_templates ───────────────────────────────────────
    op.create_table('email_templates',
        sa.Column('id',             sa.String(), primary_key=True),
        sa.Column('name',           sa.String(), nullable=False),
        sa.Column('subject',        sa.String()),
        sa.Column('html_body',      sa.Text()),
        sa.Column('plain_body',     sa.Text()),
        sa.Column('grapesjs_json',  sa.Text()),
        sa.Column('created_at',     sa.DateTime(), server_default=sa.text('NOW()')),
        sa.Column('updated_at',     sa.DateTime(), server_default=sa.text('NOW()')),
    )

    # ── contact_tags ──────────────────────────────────────────
    op.create_table('contact_tags',
        sa.Column('contact_id', sa.String(), sa.ForeignKey('contacts.id', ondelete='CASCADE')),
        sa.Column('tag',        sa.String(), nullable=False),
        sa.Column('added_at',   sa.DateTime(), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('contact_id', 'tag'),
    )
    op.create_index('ix_tags_tag', 'contact_tags', ['tag'])

    # ── ai_suggestions ────────────────────────────────────────
    op.create_table('ai_suggestions',
        sa.Column('id',         sa.String(),  primary_key=True),
        sa.Column('type',       sa.String()),
        sa.Column('content',    sa.Text()),
        sa.Column('is_read',    sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(),server_default=sa.text('NOW()')),
    )

    # ── web_tracking_events ───────────────────────────────────
    # Standard UTM-based tracking (patent-safe, NOT Marketo's token-from-social patent)
    op.create_table('web_tracking_events',
        sa.Column('id',           sa.String(),  primary_key=True),
        sa.Column('contact_id',   sa.String(),  sa.ForeignKey('contacts.id'), nullable=True),
        sa.Column('session_id',   sa.String(),  nullable=False),
        sa.Column('page_url',     sa.Text()),
        sa.Column('utm_source',   sa.String()),
        sa.Column('utm_medium',   sa.String()),
        sa.Column('utm_campaign', sa.String()),
        sa.Column('utm_content',  sa.String()),
        sa.Column('ip_address',   sa.String()),
        sa.Column('user_agent',   sa.Text()),
        sa.Column('created_at',   sa.DateTime(), server_default=sa.text('NOW()')),
    )
    op.create_index('ix_web_events_contact',  'web_tracking_events', ['contact_id'])
    op.create_index('ix_web_events_session',  'web_tracking_events', ['session_id'])
    op.create_index('ix_web_events_campaign', 'web_tracking_events', ['utm_campaign'])


def downgrade():
    for tbl in ['web_tracking_events','ai_suggestions','contact_tags',
                'email_templates','contact_activities','campaigns',
                'contact_segment_members','segments','contacts']:
        op.drop_table(tbl)
