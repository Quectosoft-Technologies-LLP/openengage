"""
HubSpot CRM Bi-directional Sync Adapter
Uses HubSpot Private App API Key (OAuth2 supported too).
Native Mautic HubSpot plugin is configured via Mautic admin UI [web:69],
this adapter handles CUSTOM field mappings and webhook inbound events.
"""
import os, asyncio, json
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy import create_engine, text
from celery import shared_task

DB_URL         = os.getenv("DATABASE_URL")
HS_API_KEY     = os.getenv("HUBSPOT_API_KEY", "")
HS_PORTAL_ID   = os.getenv("HUBSPOT_PORTAL_ID", "")
HS_BASE        = "https://api.hubapi.com"

engine = create_engine(DB_URL) if DB_URL else None


class HubSpotAdapter:
    """
    HubSpot REST API v3 adapter.
    Auth: Bearer token (Private App key).
    Supports: Contacts, Companies, Deals, Timeline Events.
    """
    def __init__(self, api_key: str = HS_API_KEY):
        self.api_key = api_key
        self.client  = httpx.AsyncClient(
            base_url=HS_BASE,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )

    # ── FIELD MAPPING ──────────────────────────────────────────
    def oe_to_hs_contact(self, contact: dict) -> dict:
        """Map OpenEngage contact → HubSpot contact properties."""
        return {
            "properties": {
                "email":       contact.get("email", ""),
                "firstname":   contact.get("first_name", ""),
                "lastname":    contact.get("last_name", ""),
                "company":     contact.get("company", ""),
                "industry":    contact.get("industry", ""),
                "jobtitle":    contact.get("job_title", ""),
                "city":        contact.get("city", ""),
                "country":     contact.get("country", ""),
                "hs_lead_status": self._lifecycle_to_hs(contact.get("lifecycle_stage", "lead")),
                "openengage_score": str(contact.get("lead_score", 0)),
            }
        }

    def hs_contact_to_oe(self, hs_contact: dict) -> dict:
        """Map HubSpot contact → OpenEngage contact fields."""
        props = hs_contact.get("properties", {})
        return {
            "email":          props.get("email", ""),
            "first_name":     props.get("firstname", ""),
            "last_name":      props.get("lastname", ""),
            "company":        props.get("company", ""),
            "industry":       props.get("industry", ""),
            "job_title":      props.get("jobtitle", ""),
            "city":           props.get("city", ""),
            "country":        props.get("country", ""),
            "lifecycle_stage": self._hs_to_lifecycle(props.get("lifecyclestage", "")),
        }

    def _lifecycle_to_hs(self, stage: str) -> str:
        return {"lead": "NEW", "mql": "OPEN", "sql": "IN_PROGRESS",
                "customer": "CONNECTED", "churned": "UNQUALIFIED"}.get(stage, "NEW")

    def _hs_to_lifecycle(self, hs_stage: str) -> str:
        return {"subscriber": "lead", "lead": "lead", "marketingqualifiedlead": "mql",
                "salesqualifiedlead": "sql", "opportunity": "sql",
                "customer": "customer", "evangelist": "customer"}.get(hs_stage.lower(), "lead")

    # ── PUSH: OpenEngage → HubSpot ────────────────────────────
    async def upsert_contact(self, contact: dict) -> dict:
        """Create or update HubSpot contact by email."""
        hs_data = self.oe_to_hs_contact(contact)
        resp = await self.client.patch(
            f"/crm/v3/objects/contacts/{contact['email']}?idProperty=email",
            json=hs_data
        )
        if resp.status_code in (200, 201):
            return {"status": "ok", "hs_id": resp.json().get("id")}
        # Create if not found
        resp2 = await self.client.post("/crm/v3/objects/contacts", json=hs_data)
        return {"status": "created" if resp2.status_code == 201 else "error",
                "hs_id": resp2.json().get("id")}

    async def upsert_contacts_batch(self, contacts: list[dict]) -> dict:
        """Batch upsert up to 100 contacts (HubSpot batch limit)."""
        inputs = [{"id": c["email"], "idProperty": "email",
                   "properties": self.oe_to_hs_contact(c)["properties"]}
                  for c in contacts[:100]]
        resp = await self.client.post(
            "/crm/v3/objects/contacts/batch/upsert",
            json={"inputs": inputs}
        )
        return {"status": resp.status_code, "results": len(resp.json().get("results", []))}

    # ── PULL: HubSpot → OpenEngage ────────────────────────────
    async def pull_recently_updated(self, limit: int = 100) -> list[dict]:
        """Pull contacts updated recently from HubSpot."""
        resp = await self.client.get(
            "/crm/v3/objects/contacts",
            params={
                "limit": limit,
                "properties": "email,firstname,lastname,company,industry,jobtitle,lifecyclestage,city,country",
                "sorts": "lastmodifieddate",
            }
        )
        if resp.status_code == 200:
            return [self.hs_contact_to_oe(r) for r in resp.json().get("results", [])]
        return []

    # ── TIMELINE EVENTS ───────────────────────────────────────
    async def log_campaign_event(self, contact_email: str, event_type: str, metadata: dict):
        """Log an OpenEngage campaign activity as a HubSpot Timeline Event."""
        # Requires HubSpot Timeline Events app configured in portal
        resp = await self.client.post(
            f"/integrations/v1/{HS_PORTAL_ID}/timeline/event",
            json={
                "eventTypeId":  os.getenv("HS_TIMELINE_EVENT_TYPE_ID", "1"),
                "id":           f"{contact_email}_{event_type}_{int(datetime.utcnow().timestamp())}",
                "email":        contact_email,
                "extraData":    {**metadata, "event_type": event_type, "source": "OpenEngage"},
                "timestamp":    int(datetime.utcnow().timestamp() * 1000),
            }
        )
        return resp.status_code

    async def close(self):
        await self.client.aclose()


# ── WEBHOOK INBOUND HANDLER (HubSpot → OpenEngage) ────────
async def handle_hubspot_webhook(payload: list[dict]):
    """
    Process inbound HubSpot webhooks.
    Subscriptions to configure in HubSpot portal:
      - contact.creation
      - contact.propertyChange (email, lifecyclestage, hs_lead_status)
      - deal.creation (map to opportunity)
    """
    updates = {}
    for event in payload:
        obj_id     = event.get("objectId")
        prop_name  = event.get("propertyName")
        prop_value = event.get("propertyValue")
        event_type = event.get("subscriptionType", "")

        if "contact" in event_type:
            if obj_id not in updates:
                updates[obj_id] = {}
            if prop_name == "email":
                updates[obj_id]["email"] = prop_value
            elif prop_name == "lifecyclestage":
                stage_map = {"lead": "lead", "marketingqualifiedlead": "mql",
                             "salesqualifiedlead": "sql", "customer": "customer"}
                updates[obj_id]["lifecycle_stage"] = stage_map.get(prop_value, "lead")
            elif prop_name == "hs_lead_status" and prop_value == "UNQUALIFIED":
                updates[obj_id]["lifecycle_stage"] = "churned"

    # Apply updates to OpenEngage contacts
    if engine and updates:
        with engine.connect() as conn:
            for hs_id, fields in updates.items():
                if "email" in fields:
                    set_clause = ", ".join(f"{k} = :{k}" for k in fields if k != "email")
                    if set_clause:
                        conn.execute(
                            text(f"UPDATE contacts SET {set_clause}, last_active_at = NOW() WHERE email = :email"),
                            {**fields}
                        )
            conn.commit()
    return {"processed": len(updates)}


# ── CELERY TASKS ──────────────────────────────────────────
@shared_task(queue="crm_sync")
def sync_to_hubspot(contact_ids: list[str]):
    adapter = HubSpotAdapter()
    loop    = asyncio.new_event_loop()
    async def _run():
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM contacts WHERE id = ANY(:ids)"), {"ids": contact_ids}
            ).fetchall()
        contacts = [dict(r._mapping) for r in rows]
        result = await adapter.upsert_contacts_batch(contacts)
        await adapter.close()
        return result
    return loop.run_until_complete(_run())


@shared_task(queue="crm_sync")
def pull_from_hubspot():
    adapter = HubSpotAdapter()
    loop    = asyncio.new_event_loop()
    async def _run():
        updated = await adapter.pull_recently_updated(limit=200)
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
                        lifecycle_stage= EXCLUDED.lifecycle_stage,
                        last_active_at = NOW()
                """), c)
            conn.commit()
        await adapter.close()
        return {"synced": len(updated)}
    return loop.run_until_complete(_run())
