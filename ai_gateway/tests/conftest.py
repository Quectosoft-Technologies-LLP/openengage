"""
pytest configuration — shared fixtures and test DB setup.
"""
import pytest
import os
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

TEST_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:testpass@localhost:5432/openengage_test")

def pytest_configure(config):
    """Set test environment before any imports."""
    os.environ.setdefault("ENV",        "test")
    os.environ.setdefault("JWT_SECRET", "test_secret_key_minimum_32_chars_x")
    os.environ.setdefault("LLM_PROVIDER", "ollama")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Run migrations once before all tests, clean up after."""
    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        conn.commit()

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.upgrade(cfg, "head")

    yield

    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        conn.commit()
    engine.dispose()
