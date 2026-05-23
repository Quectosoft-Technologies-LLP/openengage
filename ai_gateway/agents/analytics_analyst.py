"""
Analytics Analyst Agent — Interprets campaign performance using standard attribution.
Uses first-touch, last-touch, and linear attribution (NOT Adobe-patented
probabilistic multi-order attribution).
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sqlalchemy import create_engine, text
import json, os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@localhost:5432/openengage")

AGENT_PROMPT = """You are a data-driven marketing analyst with expertise in
campaign performance measurement. When given campaign metrics, you:
1. Identify top-performing and underperforming elements
2. Calculate ROI using standard formulas
3. Apply linear multi-touch attribution (not probabilistic/patented methods)
4. Identify anomalies and their likely causes
5. Give 3 prioritized optimization recommendations
6. Forecast next-period performance based on current trends

Always show your math. Output: JSON analysis + plain English recommendations."""

def linear_attribution(touchpoints: list[dict], conversion_value: float) -> dict:
    """Patent-safe standard linear attribution — equal credit to all touches."""
    n = len(touchpoints)
    if n == 0:
        return {}
    credit = conversion_value / n
    return {tp["campaign_id"]: credit for tp in touchpoints}

class AnalyticsAnalystAgent:
    def __init__(self, llm):
        self.llm = llm
        self.engine = create_engine(DB_URL)

    def get_campaign_metrics(self, campaign_id: str) -> dict:
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""SELECT c.name, c.sent_count, c.open_count, c.click_count,
                    c.conversion_count, c.revenue_attributed
                    FROM campaigns c WHERE c.id = :cid"""),
                {"cid": campaign_id}
            ).fetchone()
            if result:
                return dict(result._mapping)
        return {}

    async def run(self, state) -> dict:
        campaign_id = state.context.get("campaign_id")
        metrics = self.get_campaign_metrics(campaign_id) if campaign_id else {}
        user_query = state.messages[-1].content

        prompt = f"""Campaign Metrics: {json.dumps(metrics)}\nRequest: {user_query}"""
        response = await self.llm.ainvoke([
            SystemMessage(content=AGENT_PROMPT),
            HumanMessage(content=prompt)
        ])
        state.messages.append(AIMessage(content=response.content))
        return state
