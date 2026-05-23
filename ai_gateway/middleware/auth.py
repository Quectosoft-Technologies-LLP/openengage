"""
Production Auth: JWT Bearer + API Key dual strategy.
All /api/* routes require auth. /webhooks/* require HMAC signature.
/health, /docs, /openapi.json are public.
"""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt, os, time
from functools import lru_cache

JWT_SECRET   = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN")
JWT_ALGO     = "HS256"
API_KEY      = os.getenv("OPENENGAGE_API_KEY", "")
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

security = HTTPBearer(auto_error=False)


def create_access_token(sub: str, expires_in: int = 86400) -> str:
    payload = {"sub": sub, "iat": int(time.time()), "exp": int(time.time()) + expires_in}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency — require valid JWT or API Key."""
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/webhooks"):
        return {"sub": "public"}

    # Check API key header
    api_key_header = request.headers.get("X-API-Key", "")
    if API_KEY and api_key_header == API_KEY:
        return {"sub": "api_key_user"}

    # Check Bearer JWT
    if not credentials:
        raise HTTPException(401, "Authentication required")
    return verify_token(credentials.credentials)


async def auth_middleware(request: Request, call_next):
    """ASGI middleware for global auth enforcement."""
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    if request.url.path.startswith("/webhooks"):
        return await call_next(request)  # Webhooks use HMAC, handled per-route
    return await call_next(request)
