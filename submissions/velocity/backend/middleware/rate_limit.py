"""
Minimal in-memory rate limiter for the unauthenticated auth endpoints
(login/register are the only routes an attacker can hit without a valid
JWT, making them the brute-force/credential-stuffing surface).

Deliberately in-process (a plain dict keyed by client IP + a deque of
timestamps) rather than Redis-backed, consistent with this project's "no
Redis" constraint - this protects a single-instance deployment, which is
what this MVP targets. A multi-instance production deployment would need
a shared store instead; see docs/BUSINESS_MODEL.md's roadmap.
"""
import time
from collections import defaultdict, deque

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from config.settings import get_settings

_RATE_LIMITED_PATHS = {"/api/auth/login", "/api/auth/register"}


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path not in _RATE_LIMITED_PATHS or request.method != "POST":
            return await call_next(request)

        settings = get_settings()
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        now = time.monotonic()
        window = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS

        hits = self._hits[key]
        while hits and now - hits[0] > window:
            hits.popleft()

        if len(hits) >= settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many attempts. Please wait a moment and try again."},
                headers={"Retry-After": str(window)},
            )

        hits.append(now)
        return await call_next(request)
