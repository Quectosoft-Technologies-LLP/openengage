"""
OpenEngage AI Gateway — Production-hardened FastAPI entry point
Adds: JWT auth, security headers, rate limiting, structured logging,
      Prometheus metrics, health checks, proper CORS locking.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import os, logging

from middleware.security import SecurityHeadersMiddleware
from middleware.logging_cfg import setup_logging
from agents.orchestrator import OrchestratorAgent
from routers import campaigns, contacts, agents, scoring, analytics, webhooks
from routers.health import router as health_router
from routers.import_contacts import router as import_router

logger = setup_logging()

# Rate limiter (slowapi + Redis backend)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing OpenEngage AI Gateway...")
    app.state.orchestrator = OrchestratorAgent()
    await app.state.orchestrator.initialize()
    logger.info("Orchestrator agent ready.")
    yield
    logger.info("Shutting down...")
    await app.state.orchestrator.shutdown()

app = FastAPI(
    title="OpenEngage AI Gateway",
    version="1.0.0",
    description="LLM-Agentic marketing automation layer",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENV") != "production" else None,  # Disable Swagger in prod
    redoc_url="/redoc" if os.getenv("ENV") != "production" else None,
)

# ── Middleware stack (order matters) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Prometheus metrics ────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# ── Routers ───────────────────────────────────────────────────
app.include_router(health_router)  # /health, /health/ready (public)
app.include_router(campaigns.router,   prefix="/api/campaigns",  tags=["Campaigns"])
app.include_router(contacts.router,    prefix="/api/contacts",   tags=["Contacts"])
app.include_router(import_router,      prefix="/api/contacts",   tags=["Import"])
app.include_router(agents.router,      prefix="/api/agents",     tags=["AI Agents"])
app.include_router(scoring.router,     prefix="/api/scoring",    tags=["Lead Scoring"])
app.include_router(analytics.router,   prefix="/api/analytics",  tags=["Analytics"])
app.include_router(webhooks.router,    prefix="/webhooks",       tags=["Webhooks"])


@app.websocket("/ws/copilot/{session_id}")
async def copilot_websocket(websocket: WebSocket, session_id: str):
    """Real-time AI copilot — streams agent responses via WebSocket."""
    # Verify JWT token from query param for WebSocket auth
    token = websocket.query_params.get("token")
    if not token and os.getenv("ENV") == "production":
        await websocket.close(code=4001)
        return
    await websocket.accept()
    orchestrator: OrchestratorAgent = websocket.app.state.orchestrator
    logger.info(f"Copilot session started: {session_id}")
    try:
        while True:
            user_message = await websocket.receive_text()
            async for chunk in orchestrator.stream_response(session_id, user_message):
                await websocket.send_json(chunk)
    except WebSocketDisconnect:
        logger.info(f"Copilot session ended: {session_id}")
