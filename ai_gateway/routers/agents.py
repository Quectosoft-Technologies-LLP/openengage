"""
FastAPI router for AI Agent interactions.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class AgentRequest(BaseModel):
    session_id: str
    message: str
    context: Optional[dict] = {}

class CampaignSuggestionRequest(BaseModel):
    industry: str
    goal: str
    budget: Optional[float] = None
    audience_size: Optional[int] = None

@router.post("/chat")
async def chat_with_agent(req: AgentRequest):
    """Invoke the orchestrator agent with a message."""
    from main import app
    orchestrator = app.state.orchestrator
    results = []
    async for chunk in orchestrator.stream_response(req.session_id, req.message):
        results.append(chunk)
    final = next((r for r in reversed(results) if r["type"] == "response"), None)
    return {"response": final["content"] if final else "", "agent_used": final.get("agent") if final else None}

@router.post("/suggest-campaign")
async def suggest_campaign(req: CampaignSuggestionRequest):
    """Get AI-powered campaign suggestions for a given industry and goal."""
    from main import app
    orchestrator = app.state.orchestrator
    message = (f"Create a campaign strategy for a {req.industry} company. "
               f"Goal: {req.goal}. "
               f"{'Budget: $' + str(req.budget) + '. ' if req.budget else ''}"
               f"{'Audience: ' + str(req.audience_size) + ' contacts.' if req.audience_size else ''}")
    results = []
    async for chunk in orchestrator.stream_response("suggest_" + req.industry, message):
        results.append(chunk)
    final = next((r for r in reversed(results) if r["type"] == "response"), None)
    return {"suggestion": final["content"] if final else ""}

@router.post("/generate-email")
async def generate_email(req: AgentRequest):
    """Direct call to Email Copywriter Agent."""
    from main import app
    agent = app.state.orchestrator.agents["email_copywriter"]
    from pydantic import BaseModel as PBM
    from langchain_core.messages import HumanMessage
    class MockState(PBM):
        session_id: str
        messages: list
        current_agent: str | None = None
        context: dict = {}
    state = MockState(session_id=req.session_id,
                      messages=[HumanMessage(content=req.message)],
                      context=req.context or {})
    result = await agent.run(state)
    return {"email_content": result.messages[-1].content}

@router.get("/suggestions")
async def get_ai_suggestions(limit: int = 10):
    """Retrieve stored AI suggestions from the DB."""
    from sqlalchemy import create_engine, text
    import os
    engine = create_engine(os.getenv("DATABASE_URL", ""))
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM ai_suggestions ORDER BY created_at DESC LIMIT :lim"),
            {"lim": limit}
        ).fetchall()
    return {"suggestions": [dict(r._mapping) for r in rows]}
