"""
FastAPI endpoint tests — covers all major routes.
Uses pytest-asyncio + httpx AsyncClient against a test DB.
"""
import pytest, pytest_asyncio, asyncio, json, os
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from unittest.mock import AsyncMock, patch, MagicMock

TEST_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:testpass@localhost:5432/openengage_test")
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ENV"]            = "test"
os.environ["JWT_SECRET"]     = "test_secret_key_minimum_32_chars_x"
os.environ["LLM_PROVIDER"]   = "ollama"
os.environ["REDIS_URL"]      = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Import app AFTER setting env vars
from main import app
from middleware.auth import create_access_token


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def db_engine():
    return create_engine(TEST_DB_URL)


@pytest.fixture(scope="session")
def auth_headers():
    token = create_access_token(sub="test-user", expires_in=3600)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Health Endpoints ──────────────────────────────────────────
class TestHealth:
    @pytest.mark.asyncio
    async def test_liveness_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"
        assert data["service"] == "openengage-ai-gateway"

    @pytest.mark.asyncio
    async def test_liveness_no_auth_required(self, client):
        """Health endpoint must be public — no auth header."""
        resp = await client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_readiness_returns_status(self, client):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert "postgres" in data["checks"]
        assert "redis"    in data["checks"]


# ── Auth Tests ────────────────────────────────────────────────
class TestAuth:
    @pytest.mark.asyncio
    async def test_protected_route_without_token_returns_401(self, client):
        resp = await client.get("/api/campaigns")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_protected_route_with_valid_token(self, client, auth_headers):
        resp = await client.get("/api/campaigns", headers=auth_headers)
        assert resp.status_code in (200, 404)  # 404 OK if no campaigns yet

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, client):
        expired_token = create_access_token(sub="user", expires_in=-1)
        resp = await client.get(
            "/api/campaigns",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_auth(self, client):
        with patch.dict(os.environ, {"OPENENGAGE_API_KEY": "test-api-key-123"}):
            resp = await client.get(
                "/api/campaigns",
                headers={"X-API-Key": "test-api-key-123"}
            )
            assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, client):
        with patch.dict(os.environ, {"OPENENGAGE_API_KEY": "correct-key"}):
            resp = await client.get(
                "/api/campaigns",
                headers={"X-API-Key": "wrong-key"}
            )
            assert resp.status_code in (401, 403)


# ── Campaign Endpoints ────────────────────────────────────────
class TestCampaigns:
    @pytest.mark.asyncio
    async def test_list_campaigns(self, client, auth_headers):
        resp = await client.get("/api/campaigns", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), (list, dict))

    @pytest.mark.asyncio
    async def test_create_campaign(self, client, auth_headers, db_engine):
        payload = {
            "name":   "Test Nurture Campaign",
            "type":   "trigger",
            "status": "draft",
        }
        resp = await client.post("/api/campaigns", headers=auth_headers, json=payload)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data.get("name") == "Test Nurture Campaign"
        # Cleanup
        cid = data.get("id")
        if cid:
            with db_engine.connect() as conn:
                conn.execute(text("DELETE FROM campaigns WHERE id = :id"), {"id": cid})
                conn.commit()

    @pytest.mark.asyncio
    async def test_create_campaign_missing_name(self, client, auth_headers):
        resp = await client.post("/api/campaigns", headers=auth_headers, json={"type": "trigger"})
        assert resp.status_code == 422  # Unprocessable Entity

    @pytest.mark.asyncio
    async def test_get_nonexistent_campaign_404(self, client, auth_headers):
        resp = await client.get("/api/campaigns/nonexistent-id-xyz", headers=auth_headers)
        assert resp.status_code == 404


# ── Contact Import Endpoint ───────────────────────────────────
class TestContactImport:
    VALID_CSV = b"""email,first_name,last_name,company,lead_score
alice@test.com,Alice,Smith,Acme Inc,30
bob@test.com,Bob,Jones,BetaCorp,45
charlie@test.com,Charlie,Brown,GammaCo,10
duplicate@test.com,Dup,User,DupCorp,20
duplicate@test.com,Dup,User2,DupCorp,25
"""
    INVALID_CSV = b"""name,phone
John Doe,1234567890
Jane Doe,9876543210
"""

    @pytest.mark.asyncio
    async def test_import_valid_csv(self, client, auth_headers):
        resp = await client.post(
            "/api/contacts/import",
            headers={k: v for k, v in auth_headers.items() if k != "Content-Type"},
            files={"file": ("contacts.csv", self.VALID_CSV, "text/csv")},
            data={"on_conflict": "update"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "processing"

    @pytest.mark.asyncio
    async def test_import_non_csv_rejected(self, client, auth_headers):
        resp = await client.post(
            "/api/contacts/import",
            headers={k: v for k, v in auth_headers.items() if k != "Content-Type"},
            files={"file": ("data.xlsx", b"binary", "application/vnd.ms-excel")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_import_job_status_endpoint(self, client, auth_headers):
        # First create a job
        resp = await client.post(
            "/api/contacts/import",
            headers={k: v for k, v in auth_headers.items() if k != "Content-Type"},
            files={"file": ("c.csv", self.VALID_CSV, "text/csv")},
        )
        job_id = resp.json().get("job_id")
        # Poll status
        if job_id:
            status_resp = await client.get(
                f"/api/contacts/import/{job_id}",
                headers=auth_headers
            )
            assert status_resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_import_job_not_found(self, client, auth_headers):
        resp = await client.get("/api/contacts/import/nonexistent-job-id", headers=auth_headers)
        assert resp.status_code == 404


# ── CSV Deduplication Unit Tests (no HTTP) ────────────────────
class TestCSVDeduplication:
    def test_exact_email_dedup(self):
        from integrations.csv_import.importer import deduplicate_contacts
        contacts = [
            {"email": "alice@test.com", "first_name": "Alice", "lead_score": "10"},
            {"email": "alice@test.com", "first_name": "Alice", "lead_score": "30"},
            {"email": "bob@test.com",   "first_name": "Bob",   "lead_score": "5"},
        ]
        result = deduplicate_contacts(contacts)
        emails = [c["email"] for c in result]
        assert len(result) == 2
        assert emails.count("alice@test.com") == 1

    def test_dedup_keeps_highest_score(self):
        from integrations.csv_import.importer import deduplicate_contacts
        contacts = [
            {"email": "x@test.com", "lead_score": "10"},
            {"email": "x@test.com", "lead_score": "40"},
            {"email": "x@test.com", "lead_score": "20"},
        ]
        result = deduplicate_contacts(contacts)
        assert len(result) == 1
        assert int(result[0]["lead_score"]) == 40

    def test_empty_email_filtered(self):
        from integrations.csv_import.importer import deduplicate_contacts
        contacts = [
            {"email": "",            "first_name": "Nobody"},
            {"email": "ok@test.com", "first_name": "Someone"},
        ]
        result = deduplicate_contacts(contacts)
        assert len(result) == 1
        assert result[0]["email"] == "ok@test.com"

    def test_email_normalisation(self):
        from integrations.csv_import.importer import deduplicate_contacts
        contacts = [
            {"email": "  Alice@TEST.COM  ", "lead_score": "5"},
            {"email": "alice@test.com",      "lead_score": "15"},
        ]
        result = deduplicate_contacts(contacts)
        assert len(result) == 1
        assert result[0]["email"] == "alice@test.com"

    def test_csv_column_aliases(self):
        from integrations.csv_import.importer import parse_csv
        csv_bytes = b"E-mail,First Name,Last Name\nalice@test.com,Alice,Smith\n"
        rows, headers = parse_csv(csv_bytes)
        assert len(rows) == 1
        assert rows[0].get("email") == "alice@test.com"
        assert rows[0].get("first_name") == "Alice"

    def test_semicolon_delimiter_detected(self):
        from integrations.csv_import.importer import parse_csv
        csv_bytes = b"email;first_name;company\nalice@test.com;Alice;Acme\n"
        rows, _ = parse_csv(csv_bytes)
        assert len(rows) == 1
        assert rows[0]["email"] == "alice@test.com"

    def test_email_validation(self):
        from integrations.csv_import.importer import validate_email
        assert validate_email("user@example.com")
        assert validate_email("user.name+tag@sub.domain.co.uk")
        assert not validate_email("not-an-email")
        assert not validate_email("@missing-local.com")
        assert not validate_email("missing-at-sign.com")
        assert not validate_email("")


# ── Webhook Endpoint Tests ────────────────────────────────────
class TestWebhooks:
    @pytest.mark.asyncio
    async def test_mautic_webhook_accepted(self, client):
        payload = {
            "mautic.email_on_open": [{
                "lead": {"email": "lead@test.com", "firstname": "Lead", "points": 5}
            }]
        }
        resp = await client.post("/webhooks/mautic", json=payload)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_web_tracker_accepted(self, client):
        payload = {
            "session_id":   "sess-abc-123",
            "page_url":     "https://yoursite.com/pricing",
            "utm_source":   "google",
            "utm_campaign": "brand",
        }
        resp = await client.post("/webhooks/track", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_salesforce_webhook_accepted(self, client):
        payload = {"notifications": [{"sObject": {"Email": "sf@test.com", "Status": "Qualified"}}]}
        resp = await client.post("/webhooks/salesforce", json=payload)
        assert resp.status_code == 200


# ── LLM Registry Tests ────────────────────────────────────────
class TestLLMRegistry:
    def test_get_llm_default_is_ollama(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            from llm.registry import get_llm
            with patch("llm.registry._build_ollama") as mock_ollama:
                mock_ollama.return_value = MagicMock()
                llm = get_llm()
                mock_ollama.assert_called_once()

    def test_get_llm_openai(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test"}):
            from llm.registry import get_llm
            with patch("llm.registry._build_openai") as mock_oa:
                mock_oa.return_value = MagicMock()
                llm = get_llm(provider="openai")
                mock_oa.assert_called_once()

    def test_get_llm_claude(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            from llm.registry import get_llm
            with patch("llm.registry._build_claude") as mock_cl:
                mock_cl.return_value = MagicMock()
                get_llm(provider="claude")
                mock_cl.assert_called_once()

    def test_get_llm_falls_back_on_missing_key(self):
        """If OpenAI key missing, should fall back to Ollama."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": ""}):
            from llm.registry import get_llm
            with patch("llm.registry._build_ollama") as mock_ollama:
                mock_ollama.return_value = MagicMock()
                get_llm(provider="openai")
                mock_ollama.assert_called_once()

    def test_unknown_provider_falls_back(self):
        from llm.registry import get_llm
        with patch("llm.registry._build_ollama") as mock_ollama:
            mock_ollama.return_value = MagicMock()
            get_llm(provider="unknown_provider_xyz")
            mock_ollama.assert_called_once()

    def test_provider_info_has_all_providers(self):
        from llm.registry import PROVIDER_INFO
        required = {"ollama", "openai", "claude", "gemini", "grok", "llamacpp", "azure_openai"}
        assert required.issubset(set(PROVIDER_INFO.keys()))

    def test_provider_info_ollama_is_local(self):
        from llm.registry import PROVIDER_INFO
        assert PROVIDER_INFO["ollama"]["local"] is True
        assert PROVIDER_INFO["ollama"]["needs_key"] is False

    def test_temperature_override(self):
        from llm.registry import get_llm
        with patch("llm.registry._build_ollama") as mock_ollama:
            mock_ollama.return_value = MagicMock()
            get_llm(temperature=0.9)
            args = mock_ollama.call_args[0]
            assert args[0] == 0.9  # temperature passed through


# ── Security Headers Tests ────────────────────────────────────
class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_x_content_type_options_header(self, client):
        resp = await client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options_header(self, client):
        resp = await client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    @pytest.mark.asyncio
    async def test_request_id_header_present(self, client):
        resp = await client.get("/health")
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_response_time_header_present(self, client):
        resp = await client.get("/health")
        assert "x-response-time-ms" in resp.headers
        assert float(resp.headers["x-response-time-ms"]) >= 0
