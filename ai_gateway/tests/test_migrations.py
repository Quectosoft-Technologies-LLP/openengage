"""
Alembic migration tests.
Tests: all 3 revisions apply cleanly, downgrade works,
       indexes exist, seed data inserted (scoring_rules).
"""
import pytest
from sqlalchemy import create_engine, inspect, text
from alembic.config import Config
from alembic import command
import os

TEST_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:testpass@localhost:5432/openengage_test")


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def alembic_cfg():
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    return cfg


@pytest.fixture(scope="module", autouse=True)
def run_migrations(alembic_cfg, engine):
    """Apply all migrations before tests, tear down after."""
    # Ensure clean slate
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        conn.commit()
    command.upgrade(alembic_cfg, "head")
    yield
    command.downgrade(alembic_cfg, "base")


# ── 001_initial ───────────────────────────────────────────────
class TestInitialMigration:
    EXPECTED_TABLES = [
        "contacts", "segments", "contact_segment_members",
        "campaigns", "contact_activities", "email_templates",
        "contact_tags", "ai_suggestions", "web_tracking_events"
    ]

    def test_all_tables_created(self, engine):
        inspector = inspect(engine)
        existing  = inspector.get_table_names()
        for table in self.EXPECTED_TABLES:
            assert table in existing, f"Table '{table}' not found after migration"

    def test_contacts_columns(self, engine):
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("contacts")}
        required = {"id", "email", "first_name", "last_name", "company",
                    "lead_score", "lifecycle_stage", "custom_fields", "created_at"}
        assert required.issubset(cols), f"Missing columns: {required - cols}"

    def test_contacts_email_unique_index(self, engine):
        inspector = inspect(engine)
        indexes = {i["name"]: i for i in inspector.get_indexes("contacts")}
        assert "ix_contacts_email" in indexes
        assert indexes["ix_contacts_email"]["unique"] is True

    def test_contact_segment_members_fk(self, engine):
        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("contact_segment_members")
        fk_tables = {fk["referred_table"] for fk in fks}
        assert "contacts" in fk_tables
        assert "segments" in fk_tables

    def test_campaigns_columns(self, engine):
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("campaigns")}
        assert {"open_rate", "click_rate", "sent_count", "status"}.issubset(cols)

    def test_web_tracking_events_columns(self, engine):
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("web_tracking_events")}
        utm_cols = {"utm_source", "utm_medium", "utm_campaign", "utm_content"}
        assert utm_cols.issubset(cols), "UTM columns missing"


# ── 002_scoring_attribution ───────────────────────────────────
class TestScoringAttributionMigration:
    def test_scoring_rules_table_exists(self, engine):
        inspector = inspect(engine)
        assert "scoring_rules" in inspector.get_table_names()

    def test_scoring_rules_seeded(self, engine):
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM scoring_rules")).scalar()
        assert count == 10, f"Expected 10 seed scoring rules, got {count}"

    def test_scoring_rules_email_open_exists(self, engine):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT points FROM scoring_rules WHERE activity_type = 'email_opened'")
            ).fetchone()
        assert row is not None, "email_opened rule not found"
        assert row[0] == 5

    def test_demo_requested_highest_score(self, engine):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT points FROM scoring_rules WHERE activity_type = 'demo_requested'")
            ).fetchone()
        assert row[0] == 50

    def test_spam_negative_score(self, engine):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT points FROM scoring_rules WHERE activity_type = 'spam_reported'")
            ).fetchone()
        assert row[0] == -50

    def test_ab_test_variants_table(self, engine):
        inspector = inspect(engine)
        assert "ab_test_variants" in inspector.get_table_names()

    def test_campaign_attributions_table(self, engine):
        inspector = inspect(engine)
        assert "campaign_attributions" in inspector.get_table_names()


# ── 003_integrations ──────────────────────────────────────────
class TestIntegrationsMigration:
    def test_crm_sync_log_table(self, engine):
        inspector = inspect(engine)
        assert "crm_sync_log" in inspector.get_table_names()

    def test_csv_import_jobs_table(self, engine):
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("csv_import_jobs")}
        assert {"id", "filename", "status", "inserted", "updated",
                "duplicates_in_csv", "duplicates_in_db"}.issubset(cols)

    def test_marketo_migration_log_table(self, engine):
        inspector = inspect(engine)
        assert "marketo_migration_log" in inspector.get_table_names()


# ── Data integrity tests ──────────────────────────────────────
class TestDataIntegrity:
    def test_insert_contact(self, engine):
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO contacts (id, email, first_name, last_name, lead_score, created_at)
                VALUES ('test-001', 'test@example.com', 'Test', 'User', 25, NOW())
            """))
            conn.commit()
            row = conn.execute(
                text("SELECT email, lead_score FROM contacts WHERE id = 'test-001'")
            ).fetchone()
        assert row is not None
        assert row[0] == "test@example.com"
        assert row[1] == 25

    def test_email_unique_constraint(self, engine):
        with pytest.raises(Exception, match="unique"):
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO contacts (id, email, created_at)
                    VALUES ('test-002', 'test@example.com', NOW())
                """))
                conn.commit()

    def test_activity_foreign_key(self, engine):
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO contact_activities
                    (id, contact_id, activity_type, metadata, created_at)
                VALUES ('act-001', 'test-001', 'email_opened', '{}', NOW())
            """))
            conn.commit()
            row = conn.execute(
                text("SELECT activity_type FROM contact_activities WHERE id = 'act-001'")
            ).fetchone()
        assert row[0] == "email_opened"

    def test_invalid_contact_fk_raises(self, engine):
        with pytest.raises(Exception):
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO contact_activities
                        (id, contact_id, activity_type, created_at)
                    VALUES ('act-bad', 'nonexistent-id', 'page_visited', NOW())
                """))
                conn.commit()

    def test_downgrade_removes_all_tables(self, alembic_cfg, engine):
        """Verify downgrade to base leaves no OE tables."""
        command.downgrade(alembic_cfg, "base")
        inspector = inspect(engine)
        oe_tables = [t for t in inspector.get_table_names()
                     if t not in ("alembic_version",)]
        assert len(oe_tables) == 0, f"Tables still exist after downgrade: {oe_tables}"
        # Re-upgrade for subsequent tests
        command.upgrade(alembic_cfg, "head")
