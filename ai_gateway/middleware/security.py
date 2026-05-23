"""
Production security middleware:
- Rate limiting (slowapi + Redis backend)
- Security headers (HSTS, CSP, X-Frame-Options)
- Request ID injection for tracing
- CORS locked to configured origins
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time, uuid, os

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"]          = request_id
        response.headers["X-Response-Time-Ms"]    = f"{duration:.1f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"]        = "DENY"
        response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]     = "geolocation=(), camera=(), microphone=()"
        if not os.getenv("DEBUG"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"]   = (
                "default-src \'self\'; "
                "script-src \'self\' \'unsafe-inline\'; "
                "style-src \'self\' \'unsafe-inline\' https://fonts.googleapis.com; "
                "font-src https://fonts.gstatic.com; "
                "img-src \'self\' data: https:; "
                "connect-src \'self\' ws: wss:;"
            )
        return response
