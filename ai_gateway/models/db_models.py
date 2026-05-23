"""
SQLAlchemy models for OpenEngage.
Patent-safe: no predictive ML scoring, no probabilistic attribution stored.
"""
from sqlalchemy import (Column, String, Integer, Float, DateTime, Text,
                         Boolean, ForeignKey, JSON)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())

class Contact(Base):
    __tablename__ = "contacts"
    id             = Column(String, primary_key=True, default=gen_uuid)
    email          = Column(String, unique=True, nullable=False, index=True)
    first_name     = Column(String)
    last_name      = Column(String)
    company        = Column(String)
    industry       = Column(String)
    job_title      = Column(String)
    lead_score     = Column(Integer, default=0, index=True)  # additive rule-based
    lifecycle_stage= Column(String, default="lead")          # lead/mql/sql/customer
    country        = Column(String)
    city           = Column(String)
    custom_fields  = Column(JSON, default={})
    created_at     = Column(DateTime, server_default=func.now())
    last_active_at = Column(DateTime)
    activities     = relationship("ContactActivity", back_populates="contact")


class ContactActivity(Base):
    __tablename__ = "contact_activities"
    id            = Column(String, primary_key=True, default=gen_uuid)
    contact_id    = Column(String, ForeignKey("contacts.id"), index=True)
    activity_type = Column(String, index=True)  # email_opened, form_submitted, etc.
    metadata      = Column(JSON, default={})
    created_at    = Column(DateTime, server_default=func.now())
    contact       = relationship("Contact", back_populates="activities")


class Campaign(Base):
    __tablename__ = "campaigns"
    id               = Column(String, primary_key=True, default=gen_uuid)
    name             = Column(String, nullable=False)
    type             = Column(String, default="trigger")  # trigger / batch
    status           = Column(String, default="draft")    # draft/active/paused/completed
    segment_id       = Column(String, ForeignKey("segments.id"))
    filters          = Column(Text, default="[]")         # JSON filter rules
    flow_steps       = Column(Text, default="[]")         # JSON flow definition
    sent_count       = Column(Integer, default=0)
    open_count       = Column(Integer, default=0)
    click_count      = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)
    revenue_attributed = Column(Float, default=0.0)       # linear attribution
    open_rate        = Column(Float, default=0.0)
    click_rate       = Column(Float, default=0.0)
    created_at       = Column(DateTime, server_default=func.now())
    launched_at      = Column(DateTime)


class Segment(Base):
    __tablename__ = "segments"
    id          = Column(String, primary_key=True, default=gen_uuid)
    name        = Column(String, nullable=False)
    description = Column(Text)
    filters     = Column(Text, default="[]")  # SQL-backed filter array
    member_count= Column(Integer, default=0)
    created_at  = Column(DateTime, server_default=func.now())


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id          = Column(String, primary_key=True, default=gen_uuid)
    name        = Column(String, nullable=False)
    subject     = Column(String)
    html_body   = Column(Text)
    plain_body  = Column(Text)
    grapesjs_json = Column(Text)  # GrapesJS editor state
    created_at  = Column(DateTime, server_default=func.now())


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    id         = Column(String, primary_key=True, default=gen_uuid)
    type       = Column(String)   # weekly_campaign, score_review, etc.
    content    = Column(Text)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
