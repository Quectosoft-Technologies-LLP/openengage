"""
Production health check endpoints.
/health        — liveness probe (returns 200 if process alive)
/health/ready  — readiness probe (checks DB + Redis + Ollama)
"""
from fastapi import APIRouter
from sqlalchemy import create_engine, text
import httpx, redis, os

router = APIRouter()
DB_URL     = os.getenv("DATABASE_URL", "")
REDIS_URL  = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

@router.get("/health", tags=["Health"])
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive", "service": "openengage-ai-gateway"}

@router.get("/health/ready", tags=["Health"])
async def readiness():
    """Kubernetes readiness probe — checks all dependencies."""
    checks = {}

    # PostgreSQL
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {str(e)[:80]}"

    # Redis
    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:80]}"

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            checks["ollama"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as e:
        checks["ollama"] = f"error: {str(e)[:80]}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks
    }
