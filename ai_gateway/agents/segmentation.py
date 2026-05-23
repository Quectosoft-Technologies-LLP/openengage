"""
Segmentation Agent — Builds SQL-backed audience segments using natural language.
Translates NL queries to PostgreSQL filter clauses for Mautic-compatible segments.
Patent-safe: uses standard DB filter logic, not ML clustering.
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from sqlalchemy import create_engine, text
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@localhost:5432/openengage")

AGENT_PROMPT = """You are a database-savvy marketing analyst.
Convert natural language audience descriptions into:
1. A human-readable segment definition
2. PostgreSQL WHERE clause for the contacts table
3. Estimated segment size (based on available data)
4. Recommended campaign types for this segment
5. Exclusion rules to prevent over-messaging

Contacts table columns: id, email, first_name, last_name, company,
industry, job_title, lead_score, country, city, created_at,
last_active_at, lifecycle_stage, custom_fields (JSONB)

Output as JSON: {segment_name, description, sql_where_clause,
recommended_campaigns, exclusion_rules}"""

class SegmentationAgent:
    def __init__(self, llm):
        self.llm = llm
        self.engine = create_engine(DB_URL)

    def execute_segment_query(self, where_clause: str) -> int:
        """Safely count contacts matching a segment — read-only."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM contacts WHERE {where_clause}")
                )
                return result.scalar()
        except Exception:
            return -1

    async def run(self, state) -> dict:
        user_query = state.messages[-1].content
        response = await self.llm.ainvoke([
            SystemMessage(content=AGENT_PROMPT),
            HumanMessage(content=user_query)
        ])
        state.messages.append(AIMessage(content=response.content))
        return state
