"""
Adobe Marketo → OpenEngage Migration Tool
Exports contacts, programs, email templates, and lead scores
from Marketo REST API and imports into OpenEngage.

Uses ONLY Marketo public REST API (not patented methods).
Marketo REST API docs: https://developers.marketo.com/rest-api/
"""
import os, asyncio, json, csv
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy import create_engine, text

DB_URL              = os.getenv("DATABASE_URL")
MARKETO_CLIENT_ID   = os.getenv("MARKETO_CLIENT_ID", "")
MARKETO_CLIENT_SEC  = os.getenv("MARKETO_CLIENT_SECRET", "")
MARKETO_BASE_URL    = os.getenv("MARKETO_BASE_URL", "")  # e.g. https://xxx-yyy-zzz.mktorest.com

engine = create_engine(DB_URL) if DB_URL else None


class MarketoMigrationClient:
    """
    Read-only Marketo REST API client for migration.
    Auth: OAuth2 client_credentials grant.
    """
    def __init__(self):
        self.access_token = None
        self.client = httpx.AsyncClient(timeout=60)

    async def authenticate(self) -> bool:
        resp = await self.client.get(
            f"{MARKETO_BASE_URL}/identity/oauth/token",
            params={
                "grant_type":    "client_credentials",
                "client_id":     MARKETO_CLIENT_ID,
                "client_secret": MARKETO_CLIENT_SEC,
            }
        )
        if resp.status_code == 200:
            self.access_token = resp.json().get("access_token")
            return True
        return False

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ── EXPORT LEADS ──────────────────────────────────────────
    async def get_leads_page(self, next_page_token: Optional[str] = None) -> dict:
        """Paginate through all Marketo leads."""
        params = {
            "fields": "id,email,firstName,lastName,company,industry,title,leadScore,"
                      "leadStatus,city,country,createdAt,updatedAt",
            "batchSize": 300,
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token
        else:
            # Get paging token for full export
            token_resp = await self.client.get(
                f"{MARKETO_BASE_URL}/rest/v1/leads/describe.json",
                headers=self._headers()
            )
        resp = await self.client.get(
            f"{MARKETO_BASE_URL}/rest/v1/leads.json",
            headers=self._headers(), params=params
        )
        return resp.json() if resp.status_code == 200 else {}

    async def export_all_leads(self) -> list[dict]:
        """
        Export all leads using Marketo Bulk Export API.
        Creates an export job, polls until complete, downloads CSV.
        """
        await self.authenticate()
        # Step 1: Create bulk export job
        create_resp = await self.client.post(
            f"{MARKETO_BASE_URL}/bulk/v1/leads/export/create.json",
            headers=self._headers(),
            json={
                "fields": ["id","email","firstName","lastName","company","industry",
                           "title","leadScore","leadStatus","city","country","createdAt"],
                "format": "CSV",
                "filter": {"createdAt": {"startAt": "2010-01-01T00:00:00Z",
                                          "endAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}}
            }
        )
        job = create_resp.json().get("result", [{}])[0]
        export_id = job.get("exportId")
        if not export_id:
            return []

        # Step 2: Enqueue job
        await self.client.post(
            f"{MARKETO_BASE_URL}/bulk/v1/leads/export/{export_id}/enqueue.json",
            headers=self._headers()
        )

        # Step 3: Poll for completion
        for _ in range(60):  # max 5 min wait
            await asyncio.sleep(5)
            status_resp = await self.client.get(
                f"{MARKETO_BASE_URL}/bulk/v1/leads/export/{export_id}/status.json",
                headers=self._headers()
            )
            status = status_resp.json().get("result", [{}])[0].get("status")
            if status == "Completed":
                break
            if status in ("Failed", "Cancelled"):
                return []

        # Step 4: Download CSV
        csv_resp = await self.client.get(
            f"{MARKETO_BASE_URL}/bulk/v1/leads/export/{export_id}/file.json",
            headers=self._headers()
        )
        return self._parse_csv(csv_resp.text)

    def _parse_csv(self, csv_text: str) -> list[dict]:
        """Parse Marketo bulk export CSV into list of dicts."""
        import io
        reader = csv.DictReader(io.StringIO(csv_text))
        return list(reader)

    # ── EXPORT EMAIL TEMPLATES ────────────────────────────────
    async def export_email_templates(self) -> list[dict]:
        await self._ensure_auth()
        resp = await self.client.get(
            f"{MARKETO_BASE_URL}/rest/asset/v1/emails.json",
            headers=self._headers(),
            params={"maxReturn": 200, "status": "approved"}
        )
        return resp.json().get("result", []) if resp.status_code == 200 else []

    async def get_email_content(self, email_id: int) -> dict:
        await self._ensure_auth()
        resp = await self.client.get(
            f"{MARKETO_BASE_URL}/rest/asset/v1/email/{email_id}/content.json",
            headers=self._headers()
        )
        return resp.json().get("result", [{}])[0] if resp.status_code == 200 else {}

    async def _ensure_auth(self):
        if not self.access_token:
            await self.authenticate()

    async def close(self):
        await self.client.aclose()


# ── FIELD MAPPING: Marketo → OpenEngage ───────────────────
def marketo_lead_to_oe_contact(lead: dict) -> dict:
    """Convert Marketo lead fields to OpenEngage contact schema."""
    return {
        "email":          lead.get("email", "").lower().strip(),
        "first_name":     lead.get("firstName", ""),
        "last_name":      lead.get("lastName", ""),
        "company":        lead.get("company", ""),
        "industry":       lead.get("industry", ""),
        "job_title":      lead.get("title", ""),
        "lead_score":     _safe_int(lead.get("leadScore", 0)),
        "lifecycle_stage": _marketo_status_to_lifecycle(lead.get("leadStatus", "")),
        "city":           lead.get("city", ""),
        "country":        lead.get("country", ""),
        "custom_fields":  json.dumps({
            "marketo_id":     lead.get("id"),
            "marketo_status": lead.get("leadStatus"),
            "imported_at":    datetime.utcnow().isoformat(),
        })
    }

def _marketo_status_to_lifecycle(status: str) -> str:
    return {
        "New":           "lead",
        "Working":       "mql",
        "Open":          "mql",
        "Qualified":     "sql",
        "Unqualified":   "lead",
        "In Progress":   "sql",
        "Customer":      "customer",
    }.get(status, "lead")

def _safe_int(v) -> int:
    try: return int(v)
    except: return 0


# ── IMPORT INTO OPENENGAGE ─────────────────────────────────
def import_marketo_contacts(contacts: list[dict], batch_size: int = 500) -> dict:
    """Bulk insert Marketo contacts into OpenEngage with deduplication."""
    from integrations.csv_import.deduplication import deduplicate_contacts
    deduped = deduplicate_contacts(contacts, key_field="email")
    imported = 0
    skipped  = 0
    errors   = 0

    with engine.connect() as conn:
        for i in range(0, len(deduped), batch_size):
            batch = deduped[i:i+batch_size]
            for c in batch:
                if not c.get("email"):
                    skipped += 1
                    continue
                try:
                    conn.execute(text("""
                        INSERT INTO contacts (id, email, first_name, last_name, company,
                            industry, job_title, lead_score, lifecycle_stage,
                            city, country, custom_fields, created_at)
                        VALUES (gen_random_uuid()::text, :email, :first_name, :last_name,
                            :company, :industry, :job_title, :lead_score,
                            :lifecycle_stage, :city, :country, :custom_fields::jsonb, NOW())
                        ON CONFLICT (email) DO UPDATE SET
                            first_name     = EXCLUDED.first_name,
                            last_name      = EXCLUDED.last_name,
                            company        = EXCLUDED.company,
                            industry       = EXCLUDED.industry,
                            lead_score     = GREATEST(contacts.lead_score, EXCLUDED.lead_score),
                            lifecycle_stage= EXCLUDED.lifecycle_stage,
                            last_active_at = NOW()
                    """), c)
                    imported += 1
                except Exception as e:
                    errors += 1
        conn.commit()

    return {"total": len(contacts), "imported": imported, "skipped": skipped,
            "deduplicated": len(contacts) - len(deduped), "errors": errors}


# ── CLI RUNNER ─────────────────────────────────────────────
async def run_full_migration():
    """Full Marketo → OpenEngage migration pipeline."""
    print("🚀 Starting Marketo → OpenEngage migration...")
    client = MarketoMigrationClient()
    await client.authenticate()

    print("📥 Exporting Marketo leads (bulk export)...")
    raw_leads = await client.export_all_leads()
    print(f"   Got {len(raw_leads)} leads from Marketo")

    oe_contacts = [marketo_lead_to_oe_contact(l) for l in raw_leads]

    print("💾 Importing into OpenEngage with deduplication...")
    result = import_marketo_contacts(oe_contacts)
    print(f"   ✅ Imported: {result['imported']} | Deduped: {result['deduplicated']} | Errors: {result['errors']}")

    print("📧 Exporting email templates...")
    templates = await client.export_email_templates()
    print(f"   Got {len(templates)} email templates")

    with engine.connect() as conn:
        for tmpl in templates:
            content = await client.get_email_content(tmpl["id"])
            conn.execute(text("""
                INSERT INTO email_templates (id, name, subject, html_body, created_at)
                VALUES (gen_random_uuid()::text, :name, :subject, :html_body, NOW())
                ON CONFLICT DO NOTHING
            """), {
                "name":      tmpl.get("name", "Imported Template"),
                "subject":   tmpl.get("subject", ""),
                "html_body": str(content),
            })
        conn.commit()
    print(f"   ✅ Imported {len(templates)} templates")
    await client.close()
    print("✅ Migration complete!")


if __name__ == "__main__":
    asyncio.run(run_full_migration())
