"""
Lead Scoring Agent — Patent-safe: rule-based additive scoring.
NO sentiment weighting, NO time-decay probability distributions (patented by Adobe).
Uses transparent, auditable rules configurable by marketers.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sqlalchemy import create_engine, text
import json, os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@localhost:5432/openengage")

# Patent-safe additive scoring rules — no ML weighting
DEFAULT_SCORE_RULES = {
    "email_opened":          5,
    "email_clicked":        10,
    "form_submitted":       25,
    "page_visited":          2,
    "pricing_page_visited": 15,
    "demo_requested":       50,
    "webinar_attended":     30,
    "content_downloaded":   20,
    "email_unsubscribed":  -10,
    "spam_reported":       -50,
}

AGENT_PROMPT = """You are a lead qualification expert.
Analyze the provided contact activity log and scoring rules, then:
1. Explain the current score and what drove it
2. Identify the top 3 actions that most indicate buying intent
3. Recommend adjustments to scoring rules if patterns suggest miscalibration
4. Classify the lead: Cold / Warm / Hot / MQL / SQL
5. Suggest next best action for the sales/marketing team

Output as structured JSON with a human-readable summary."""

class LeadScoringAgent:
    def __init__(self, llm):
        self.llm = llm
        self.engine = create_engine(DB_URL)

    def calculate_score(self, activities: list[dict]) -> int:
        """Patent-safe: simple additive scoring."""
        return sum(DEFAULT_SCORE_RULES.get(a.get("type", ""), 0) for a in activities)

    def get_contact_activities(self, contact_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT activity_type as type, created_at FROM contact_activities "
                     "WHERE contact_id = :cid ORDER BY created_at DESC LIMIT 100"),
                {"cid": contact_id}
            )
            return [dict(r) for r in result]

    async def run(self, state) -> dict:
        user_query = state.messages[-1].content
        contact_id = state.context.get("contact_id")
        activities = self.get_contact_activities(contact_id) if contact_id else []
        score = self.calculate_score(activities)

        prompt = f"""
Contact ID: {contact_id}
Current Score: {score}
Recent Activities: {json.dumps(activities[:20], default=str)}
Scoring Rules: {json.dumps(DEFAULT_SCORE_RULES)}
Request: {user_query}
"""
        response = await self.llm.ainvoke([
            SystemMessage(content=AGENT_PROMPT),
            HumanMessage(content=prompt)
        ])
        state.messages.append(AIMessage(content=response.content))
        return state
