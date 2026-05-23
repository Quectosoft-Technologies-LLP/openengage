"""
Inbound Webhook Router — receives events from:
  - HubSpot   (contact.propertyChange, contact.creation, deal.creation)
  - Salesforce (via Apex callouts or MuleSoft)
  - Mautic     (webhook plugin — contact updated, form submitted)
  - OpenEngage web tracker (page views, form submits)
"""
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from typing import Optional
import hmac, hashlib, json, os
from sqlalchemy import create_engine, text
import uuid

router  = APIRouter()
DB_URL  = os.getenv("DATABASE_URL")
engine  = create_engine(DB_URL) if DB_URL else None

HS_WEBHOOK_SECRET  = os.getenv("HUBSPOT_WEBHOOK_SECRET", "")
SF_WEBHOOK_SECRET  = os.getenv("SF_WEBHOOK_SECRET", "")
OE_TRACKER_SECRET  = os.getenv("OE_TRACKER_SECRET", "openengage-tracker")


# ── HUBSPOT INBOUND ───────────────────────────────────────────
@router.post("/hubspot")
async def hubspot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hubspot_signature: Optional[str] = Header(None)
):
    body = await request.body()
    # Verify HubSpot HMAC signature
    if HS_WEBHOOK_SECRET:
        expected = hmac.new(
            HS_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, x_hubspot_signature or ""):
            raise HTTPException(status_code=403, detail="Invalid HubSpot signature")

    payload = json.loads(body)
    from integrations.hubspot.adapter import handle_hubspot_webhook
    background_tasks.add_task(handle_hubspot_webhook, payload)
    return {"status": "queued", "events": len(payload)}


# ── SALESFORCE INBOUND (Apex Outbound Message) ────────────────
@router.post("/salesforce")
async def salesforce_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives Salesforce Outbound Messages (SOAP-based) or
    custom Platform Events forwarded via MuleSoft/middleware.
    """
    body = await request.json()
    background_tasks.add_task(_process_sf_event, body)
    # SF Outbound Messages require ACK
    return {"<soapenv:Envelope>": "<ack>true</ack>"}

async def _process_sf_event(event: dict):
    """Update OpenEngage contact from Salesforce event."""
    notifications = event.get("notifications", [event])
    if not engine: return
    with engine.connect() as conn:
        for notif in notifications:
            sf_obj = notif.get("sObject", notif)
            email  = sf_obj.get("Email")
            if not email: continue
            conn.execute(text("""
                UPDATE contacts SET
                    lifecycle_stage = CASE
                        WHEN :sf_status = 'Converted' THEN 'customer'
                        WHEN :sf_status = 'Qualified' THEN 'sql'
                        WHEN :sf_status = 'Working'   THEN 'mql'
                        ELSE lifecycle_stage
                    END,
                    last_active_at = NOW()
                WHERE email = :email
            """), {"email": email, "sf_status": sf_obj.get("Status", "")})
        conn.commit()


# ── MAUTIC INBOUND (Mautic Webhook Plugin) ────────────────────
@router.post("/mautic")
async def mautic_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives events from Mautic webhook plugin.
    Configure in Mautic: Settings → Webhooks → Add Webhook
    Events: mautic.lead_post_save_new, mautic.lead_post_save_update,
            mautic.form_on_submit, mautic.email_on_open, mautic.email_on_click
    """
    payload = await request.json()
    background_tasks.add_task(_process_mautic_event, payload)
    return {"status": "received"}

async def _process_mautic_event(payload: dict):
    """Sync Mautic contact updates into OpenEngage contacts table."""
    if not engine: return
    for event_type, events in payload.items():
        if not isinstance(events, list):
            events = [events]
        with engine.connect() as conn:
            for event in events:
                lead = event.get("lead", event.get("contact", {}))
                email = lead.get("fields", {}).get("core", {}).get("email", {}).get("value")
                if not email: email = lead.get("email")
                if not email: continue

                # Upsert contact from Mautic data
                conn.execute(text("""
                    INSERT INTO contacts
                        (id, email, first_name, last_name, company, lead_score, created_at)
                    VALUES
                        (gen_random_uuid()::text, :email, :first_name, :last_name, :company, :score, NOW())
                    ON CONFLICT (email) DO UPDATE SET
                        first_name = COALESCE(NULLIF(EXCLUDED.first_name,''), contacts.first_name),
                        last_name  = COALESCE(NULLIF(EXCLUDED.last_name,''),  contacts.last_name),
                        company    = COALESCE(NULLIF(EXCLUDED.company,''),    contacts.company),
                        last_active_at = NOW()
                """), {
                    "email":      email,
                    "first_name": lead.get("firstname", ""),
                    "last_name":  lead.get("lastname", ""),
                    "company":    lead.get("company", ""),
                    "score":      int(lead.get("points", 0)),
                })

                # Log activity
                activity_map = {
                    "mautic.email_on_open":  "email_opened",
                    "mautic.email_on_click": "email_clicked",
                    "mautic.form_on_submit": "form_submitted",
                }
                act_type = activity_map.get(event_type)
                if act_type:
                    contact_row = conn.execute(
                        text("SELECT id FROM contacts WHERE email = :e"), {"e": email}
                    ).fetchone()
                    if contact_row:
                        conn.execute(text("""
                            INSERT INTO contact_activities
                                (id, contact_id, activity_type, metadata, created_at)
                            VALUES (gen_random_uuid()::text, :cid, :type, :meta::jsonb, NOW())
                        """), {
                            "cid":  contact_row.id,
                            "type": act_type,
                            "meta": json.dumps({"source": "mautic", "event": event_type})
                        })
            conn.commit()


# ── OPENENGAGE WEB TRACKER (JS Snippet) ──────────────────────
@router.post("/track")
async def web_tracker(request: Request):
    """
    Receives events from the OpenEngage web tracking JS snippet.
    Collects: page_url, utm_*, session_id, optional email.
    PATENT-SAFE: Uses standard UTM parameters only.
    """
    data       = await request.json()
    session_id = data.get("session_id", str(uuid.uuid4()))
    contact_id = None

    if not engine:
        return {"status": "ok"}

    with engine.connect() as conn:
        # Try to resolve contact by email if provided
        if data.get("email"):
            row = conn.execute(
                text("SELECT id FROM contacts WHERE email = :e"),
                {"e": data["email"].lower().strip()}
            ).fetchone()
            if row: contact_id = row.id

        # Insert tracking event
        conn.execute(text("""
            INSERT INTO web_tracking_events
                (id, contact_id, session_id, page_url, utm_source, utm_medium,
                 utm_campaign, utm_content, ip_address, user_agent, created_at)
            VALUES
                (gen_random_uuid()::text, :cid, :session_id, :page_url, :utm_source,
                 :utm_medium, :utm_campaign, :utm_content, :ip, :ua, NOW())
        """), {
            "cid":          contact_id,
            "session_id":   session_id,
            "page_url":     data.get("page_url", ""),
            "utm_source":   data.get("utm_source", ""),
            "utm_medium":   data.get("utm_medium", ""),
            "utm_campaign": data.get("utm_campaign", ""),
            "utm_content":  data.get("utm_content", ""),
            "ip":           request.client.host if request.client else "",
            "ua":           request.headers.get("user-agent", ""),
        })

        # Log page visit activity if contact known
        if contact_id:
            page_url = data.get("page_url", "")
            act_type = "pricing_page_visited" if "pricing" in page_url.lower() else "page_visited"
            conn.execute(text("""
                INSERT INTO contact_activities (id, contact_id, activity_type, metadata, created_at)
                VALUES (gen_random_uuid()::text, :cid, :type, :meta::jsonb, NOW())
            """), {
                "cid":  contact_id,
                "type": act_type,
                "meta": json.dumps({"page_url": page_url, "session_id": session_id})
            })
        conn.commit()

    return {"status": "ok", "session_id": session_id}
