"""
Celery tasks for campaign execution, email delivery, lead scoring, and agent dispatch.
"""
from workers.celery_app import celery_app
from sqlalchemy import create_engine, text
import httpx, os, json

DB_URL = os.getenv("DATABASE_URL")
POSTAL_API = os.getenv("POSTAL_API_URL", "http://postal:5000/api/v1")
POSTAL_KEY = os.getenv("POSTAL_API_KEY", "")
MAUTIC_URL = os.getenv("MAUTIC_URL", "http://mautic:80")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

engine = create_engine(DB_URL) if DB_URL else None

@celery_app.task(bind=True, max_retries=3, queue="campaign")
def run_trigger_campaign(self, campaign_id: str, contact_id: str):
    """Execute a trigger-based campaign for one contact."""
    try:
        with engine.connect() as conn:
            campaign = conn.execute(
                text("SELECT * FROM campaigns WHERE id = :id"), {"id": campaign_id}
            ).fetchone()
            if not campaign:
                return {"status": "error", "message": "Campaign not found"}

            contact = conn.execute(
                text("SELECT * FROM contacts WHERE id = :id"), {"id": contact_id}
            ).fetchone()

            # Evaluate filters (standard SQL-based, not ML)
            filters_pass = evaluate_campaign_filters(conn, campaign, contact_id)
            if not filters_pass:
                return {"status": "filtered_out", "contact_id": contact_id}

            # Execute flow steps sequentially
            flow_steps = json.loads(campaign.flow_steps or "[]")
            for step in flow_steps:
                execute_flow_step.apply_async(
                    args=[step, dict(contact._mapping)],
                    countdown=step.get("delay_minutes", 0) * 60
                )
        return {"status": "queued", "contact_id": contact_id, "steps": len(flow_steps)}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, queue="campaign")
def run_batch_campaign(self, campaign_id: str):
    """Execute a batch campaign — queues trigger tasks for all qualified contacts."""
    with engine.connect() as conn:
        campaign = conn.execute(
            text("SELECT * FROM campaigns WHERE id = :id"), {"id": campaign_id}
        ).fetchone()
        segment_id = campaign.segment_id
        contacts = conn.execute(
            text("SELECT id FROM contact_segment_members WHERE segment_id = :sid"),
            {"sid": segment_id}
        ).fetchall()

    for contact_row in contacts:
        run_trigger_campaign.apply_async(args=[campaign_id, str(contact_row.id)])
    return {"status": "dispatched", "total": len(contacts)}


@celery_app.task(bind=True, max_retries=3, queue="email")
def send_email(self, to_email: str, subject: str, html_body: str, plain_body: str = ""):
    """Send via Postal MTA API."""
    try:
        with httpx.Client() as client:
            resp = client.post(
                f"{POSTAL_API}/send/message",
                headers={"X-Server-API-Key": POSTAL_KEY},
                json={
                    "to": [to_email],
                    "subject": subject,
                    "html_body": html_body,
                    "plain_body": plain_body,
                }
            )
            resp.raise_for_status()
        return {"status": "sent", "to": to_email}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(queue="scoring")
def update_lead_scores():
    """Recalculate lead scores for all contacts — additive rule-based (patent-safe)."""
    SCORE_RULES = {
        "email_opened": 5, "email_clicked": 10,
        "form_submitted": 25, "page_visited": 2,
        "pricing_page_visited": 15, "demo_requested": 50,
    }
    with engine.connect() as conn:
        contacts = conn.execute(text("SELECT DISTINCT contact_id FROM contact_activities")).fetchall()
        for row in contacts:
            cid = row.contact_id
            activities = conn.execute(
                text("SELECT activity_type FROM contact_activities WHERE contact_id = :cid"),
                {"cid": cid}
            ).fetchall()
            score = sum(SCORE_RULES.get(a.activity_type, 0) for a in activities)
            conn.execute(
                text("UPDATE contacts SET lead_score = :score WHERE id = :cid"),
                {"score": score, "cid": cid}
            )
        conn.commit()


@celery_app.task(queue="agents")
def generate_campaign_suggestions():
    """Weekly task: ask the Campaign Strategy Agent for proactive recommendations."""
    import asyncio
    from agents.campaign_strategy import CampaignStrategyAgent
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model="qwen3:8b", base_url=OLLAMA_URL)
    agent = CampaignStrategyAgent(llm)

    with engine.connect() as conn:
        stats = conn.execute(text("""
            SELECT AVG(open_rate) as avg_open, AVG(click_rate) as avg_click,
                   COUNT(*) as total_campaigns
            FROM campaigns WHERE created_at > NOW() - INTERVAL '30 days'
        """)).fetchone()

    from pydantic import BaseModel
    from langchain_core.messages import HumanMessage

    class MockState(BaseModel):
        session_id: str = "weekly_suggestion"
        messages: list = [HumanMessage(
            content=f"Based on last 30 days: avg open {stats.avg_open:.1f}%, "
                    f"click {stats.avg_click:.1f}%, {stats.total_campaigns} campaigns. "
                    f"Suggest 3 new campaign strategies for next month."
        )]
        current_agent: str | None = None
        context: dict = {}

    result = asyncio.run(agent.run(MockState()))
    # Store suggestion in DB for UI display
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO ai_suggestions (type, content, created_at) VALUES (:t, :c, NOW())"
        ), {"t": "weekly_campaign", "c": result.messages[-1].content})
        conn.commit()


def evaluate_campaign_filters(conn, campaign, contact_id: str) -> bool:
    """Evaluate campaign filter rules against a contact — standard SQL logic."""
    filters = json.loads(campaign.filters or "[]")
    if not filters:
        return True
    filter_clauses = " AND ".join(
        f"{f['field']} {f['operator']} '{f['value']}'"
        for f in filters if all(k in f for k in ["field", "operator", "value"])
    )
    if not filter_clauses:
        return True
    result = conn.execute(
        text(f"SELECT 1 FROM contacts WHERE id = :cid AND ({filter_clauses})"),
        {"cid": contact_id}
    ).fetchone()
    return result is not None


@celery_app.task(queue="campaign")
def execute_flow_step(step: dict, contact: dict):
    """Execute a single flow step (email, SMS, tag, score)."""
    step_type = step.get("type")
    if step_type == "send_email":
        html = step.get("html_body", "").replace("{{first_name}}", contact.get("first_name", ""))
        send_email.apply_async(args=[
            contact["email"],
            step.get("subject", ""),
            html
        ])
    elif step_type == "add_tag":
        engine.execute(
            text("INSERT INTO contact_tags (contact_id, tag) VALUES (:cid, :tag) ON CONFLICT DO NOTHING"),
            {"cid": contact["id"], "tag": step.get("tag", "")}
        )
    elif step_type == "adjust_score":
        engine.execute(
            text("UPDATE contacts SET lead_score = lead_score + :delta WHERE id = :cid"),
            {"delta": step.get("delta", 0), "cid": contact["id"]}
        )
