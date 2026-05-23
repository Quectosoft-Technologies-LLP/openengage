"""
Salesforce CRM Bi-directional Sync Adapter
- OAuth2 authentication (no patented logic)
- Push Mautic contacts → Salesforce Leads/Contacts
- Pull Salesforce updates → OpenEngage contacts
- Sync campaign activities → Salesforce Timeline (standard API only)
"""
import os, json, asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
from sqlalchemy import create_engine, text
from celery import shared_task

DB_URL          = os.getenv("DATABASE_URL")
SF_CLIENT_ID    = os.getenv("SF_CLIENT_ID", "")
SF_CLIENT_SECRET= os.getenv("SF_CLIENT_SECRET", "")
SF_USERNAME     = os.getenv("SF_USERNAME", "")
SF_PASSWORD     = os.getenv("SF_PASSWORD", "")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "")
SF_INSTANCE_URL = os.getenv("SF_INSTANCE_URL", "https://login.salesforce.com")

engine = create_engine(DB_URL) if DB_URL else None


class SalesforceAdapter:
    """
    Standard Salesforce REST API adapter.
    Uses OAuth2 username-password flow for server-to-server sync.
    """
    def __init__(self):
        self.access_token  = None
        self.instance_url  = None
        self.token_expiry  = None
        self.client        = httpx.AsyncClient(timeout=30)

    async def authenticate(self) -> bool:
        """OAuth2 username-password flow — standard, not patented."""
        resp = await self.client.post(
            f"{SF_INSTANCE_URL}/services/oauth2/token",
            data={
                "grant_type":    "password",
                "client_id":     SF_CLIENT_ID,
                "client_secret": SF_CLIENT_SECRET,
                "username":      SF_USERNAME,
                "password":      SF_PASSWORD + SF_SECURITY_TOKEN,
            }
        )
        if resp.status_code == 200:
            data = resp.json()
            self.access_token = data["access_token"]
            self.instance_url = data["instance_url"]
            self.token_expiry = datetime.utcnow() + timedelta(hours=1)
            return True
        return False

    async def _ensure_auth(self):
        if not self.access_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json",
        }

    # ── CONTACT FIELD MAPPING ──────────────────────────────────
    def oe_to_sf_lead(self, contact: dict) -> dict:
        """Map OpenEngage contact fields → Salesforce Lead fields."""
        return {
            "FirstName":   contact.get("first_name", ""),
            "LastName":    contact.get("last_name", "Unknown"),
            "Email":       contact.get("email", ""),
            "Company":     contact.get("company", "Unknown"),
            "Industry":    contact.get("industry", ""),
            "Title":       contact.get("job_title", ""),
            "LeadSource":  "OpenEngage",
            "Rating":      self._score_to_sf_rating(contact.get("lead_score", 0)),
            "Description": f"OpenEngage Contact ID: {contact.get('id')} | Score: {contact.get('lead_score', 0)}",
        }

    def sf_lead_to_oe(self, sf_lead: dict) -> dict:
        """Map Salesforce Lead → OpenEngage contact fields."""
        return {
            "first_name":     sf_lead.get("FirstName", ""),
            "last_name":      sf_lead.get("LastName", ""),
            "email":          sf_lead.get("Email", ""),
            "company":        sf_lead.get("Company", ""),
            "industry":       sf_lead.get("Industry", ""),
            "job_title":      sf_lead.get("Title", ""),
            "lifecycle_stage": self._sf_status_to_lifecycle(sf_lead.get("Status", "")),
        }

    def _score_to_sf_rating(self, score: int) -> str:
        if score >= 50: return "Hot"
        if score >= 25: return "Warm"
        return "Cold"

    def _sf_status_to_lifecycle(self, status: str) -> str:
        mapping = {
            "Open":         "lead",
            "Working":      "mql",
            "Qualified":    "sql",
            "Converted":    "customer",
            "Unqualified":  "lead",
        }
        return mapping.get(status, "lead")

    # ── PUSH: OpenEngage → Salesforce ─────────────────────────
    async def push_contact(self, contact: dict) -> dict:
        """Upsert contact to Salesforce Lead using email as external ID."""
        await self._ensure_auth()
        sf_data = self.oe_to_sf_lead(contact)
        # Use PATCH upsert on Email field
        resp = await self.client.patch(
            f"{self.instance_url}/services/data/v59.0/sobjects/Lead/Email/{contact['email']}",
            headers=self._headers(),
            json=sf_data
        )
        return {"status": resp.status_code, "contact": contact["email"]}

    async def push_contacts_batch(self, contacts: list[dict]) -> list[dict]:
        """Batch upsert up to 200 contacts using Salesforce Composite API."""
        await self._ensure_auth()
        records = []
        for c in contacts[:200]:
            records.append({
                "method": "PATCH",
                "url":    f"/services/data/v59.0/sobjects/Lead/Email/{c['email']}",
                "body":   self.oe_to_sf_lead(c),
                "referenceId": c["id"]
            })
        resp = await self.client.post(
            f"{self.instance_url}/services/data/v59.0/composite",
            headers=self._headers(),
            json={"allOrNone": False, "compositeRequest": records}
        )
        return resp.json().get("compositeResponse", [])

    # ── PULL: Salesforce → OpenEngage ─────────────────────────
    async def pull_updated_leads(self, since_minutes: int = 30) -> list[dict]:
        """Pull Salesforce leads updated in the last N minutes."""
        await self._ensure_auth()
        since = (datetime.utcnow() - timedelta(minutes=since_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
        soql = (
            f"SELECT Id,FirstName,LastName,Email,Company,Industry,Title,Status,"
            f"LastModifiedDate FROM Lead WHERE LastModifiedDate > {since} AND Email != null"
        )
        resp = await self.client.get(
            f"{self.instance_url}/services/data/v59.0/query",
            headers=self._headers(),
            params={"q": soql}
        )
        if resp.status_code == 200:
            return [self.sf_lead_to_oe(r) for r in resp.json().get("records", [])]
        return []

    async def sync_activities_to_sf(self, contact_id: str, activities: list[dict]):
        """Push OpenEngage activities to Salesforce as Tasks (standard API)."""
        await self._ensure_auth()
        # Lookup SF Lead ID by email
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT email FROM contacts WHERE id = :id"), {"id": contact_id}
            ).fetchone()
        if not row: return

        soql = f"SELECT Id FROM Lead WHERE Email = '{row.email}' LIMIT 1"
        resp = await self.client.get(
            f"{self.instance_url}/services/data/v59.0/query",
            headers=self._headers(), params={"q": soql}
        )
        sf_records = resp.json().get("records", [])
        if not sf_records: return
        sf_lead_id = sf_records[0]["Id"]

        for act in activities:
            await self.client.post(
                f"{self.instance_url}/services/data/v59.0/sobjects/Task",
                headers=self._headers(),
                json={
                    "WhoId":      sf_lead_id,
                    "Subject":    f"OpenEngage: {act.get('activity_type', 'Activity')}",
                    "Status":     "Completed",
                    "ActivityDate": datetime.utcnow().strftime("%Y-%m-%d"),
                    "Description": json.dumps(act.get("metadata", {})),
                }
            )

    async def close(self):
        await self.client.aclose()


# ── CELERY TASKS ───────────────────────────────────────────
@shared_task(queue="crm_sync")
def sync_to_salesforce(contact_ids: list[str]):
    """Push a batch of contacts to Salesforce."""
    adapter = SalesforceAdapter()
    loop = asyncio.new_event_loop()

    async def _run():
        await adapter.authenticate()
        with engine.connect() as conn:
            rows = conn.execute(
                text(f"SELECT * FROM contacts WHERE id = ANY(:ids)"),
                {"ids": contact_ids}
            ).fetchall()
        contacts = [dict(r._mapping) for r in rows]
        results = await adapter.push_contacts_batch(contacts)
        await adapter.close()
        return results

    return loop.run_until_complete(_run())


@shared_task(queue="crm_sync")
def pull_from_salesforce():
    """Pull recent Salesforce updates and merge into OpenEngage contacts."""
    adapter = SalesforceAdapter()
    loop = asyncio.new_event_loop()

    async def _run():
        await adapter.authenticate()
        updated = await adapter.pull_updated_leads(since_minutes=35)
        with engine.connect() as conn:
            for c in updated:
                if not c.get("email"): continue
                conn.execute(text("""
                    INSERT INTO contacts (id, email, first_name, last_name, company,
                                         industry, job_title, lifecycle_stage, created_at)
                    VALUES (gen_random_uuid()::text, :email, :first_name, :last_name,
                            :company, :industry, :job_title, :lifecycle_stage, NOW())
                    ON CONFLICT (email) DO UPDATE SET
                        first_name     = EXCLUDED.first_name,
                        last_name      = EXCLUDED.last_name,
                        company        = EXCLUDED.company,
                        industry       = EXCLUDED.industry,
                        job_title      = EXCLUDED.job_title,
                        lifecycle_stage= EXCLUDED.lifecycle_stage,
                        last_active_at = NOW()
                """), c)
            conn.commit()
        await adapter.close()
        return {"synced": len(updated)}

    return loop.run_until_complete(_run())
