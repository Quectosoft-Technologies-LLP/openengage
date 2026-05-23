"""
OpenEngage Orchestrator Agent — LangGraph Supervisor
Updated to use the universal LLM registry (any provider, zero agent changes).
"""
from __future__ import annotations
import logging
from typing import AsyncIterator
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from llm.registry import get_llm, get_embeddings
from agents.campaign_strategy import CampaignStrategyAgent
from agents.lead_scoring     import LeadScoringAgent
from agents.email_copywriter import EmailCopywriterAgent
from agents.segmentation     import SegmentationAgent
from agents.analytics_analyst import AnalyticsAnalystAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Supervisor that routes user requests to specialist agents.
    LLM is resolved from LLM_PROVIDER env var — default Ollama.
    Swap provider by changing one env var, no code changes needed.
    """

    ROUTING_KEYWORDS = {
        "campaign_strategy": [
            "campaign", "nurture", "sequence", "drip", "workflow",
            "strategy", "plan", "program", "journey", "automation"
        ],
        "lead_scoring": [
            "score", "scoring", "points", "qualify", "mql", "sql",
            "hot lead", "lead quality", "rank", "prioritize"
        ],
        "email_copywriter": [
            "subject", "email", "write", "copy", "headline",
            "a/b", "variant", "draft", "compose", "newsletter"
        ],
        "segmentation": [
            "segment", "audience", "filter", "who", "contacts",
            "list", "group", "show me", "find contacts", "sql"
        ],
        "analytics_analyst": [
            "analytics", "report", "roi", "attribution", "performance",
            "open rate", "click rate", "revenue", "conversion", "metric"
        ],
    }

    def __init__(self):
        self.llm        = None
        self.embeddings = None
        self.agents     = {}

    async def initialize(self):
        """Lazy-initialize LLM and all sub-agents."""
        self.llm        = get_llm()                # Reads LLM_PROVIDER from env
        self.embeddings = get_embeddings()
        self.agents = {
            "campaign_strategy": CampaignStrategyAgent(self.llm, self.embeddings),
            "lead_scoring":      LeadScoringAgent(self.llm),
            "email_copywriter":  EmailCopywriterAgent(self.llm),
            "segmentation":      SegmentationAgent(self.llm),
            "analytics_analyst": AnalyticsAnalystAgent(self.llm),
        }
        logger.info(f"Orchestrator initialized with agents: {list(self.agents.keys())}")

    def _route(self, message: str) -> str:
        """Keyword-based routing — deterministic, no LLM call needed."""
        msg_lower = message.lower()
        scores = {agent: 0 for agent in self.ROUTING_KEYWORDS}
        for agent, keywords in self.ROUTING_KEYWORDS.items():
            for kw in keywords:
                if kw in msg_lower:
                    scores[agent] += 1
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "campaign_strategy"

    async def stream_response(
        self, session_id: str, user_message: str
    ) -> AsyncIterator[dict]:
        """
        Stream agent response chunks to WebSocket.
        Yields dicts: { "type": "thinking"|"response"|"done", "content": str, "agent": str }
        """
        agent_name = self._route(user_message)
        agent      = self.agents.get(agent_name)

        yield {"type": "thinking", "content": f"Routing to {agent_name.replace('_', ' ').title()} Agent...", "agent": agent_name}

        if not agent:
            yield {"type": "response", "content": "Agent not available.", "agent": "orchestrator"}
            yield {"type": "done",     "content": "", "agent": agent_name}
            return

        try:
            full_response = await agent.run(user_message)
            # Stream in chunks for realistic streaming UX
            words = full_response.split()
            chunk_size = 8
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i+chunk_size])
                yield {"type": "response", "content": chunk + " ", "agent": agent_name}
        except Exception as e:
            logger.error(f"Agent {agent_name} error: {e}")
            yield {"type": "response", "content": f"Agent error: {str(e)[:200]}", "agent": agent_name}

        yield {"type": "done", "content": "", "agent": agent_name}

    async def run_sync(self, session_id: str, user_message: str) -> dict:
        """Non-streaming version for REST endpoints."""
        agent_name = self._route(user_message)
        agent      = self.agents.get(agent_name)
        if not agent:
            return {"agent": agent_name, "response": "Agent not available"}
        response = await agent.run(user_message)
        return {"agent": agent_name, "response": response}

    async def shutdown(self):
        logger.info("Orchestrator shutting down.")
