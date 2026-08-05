"""Lightweight request logging middleware (no external log infra required)."""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("promptshield")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Previously this exception propagated straight through the
            # middleware, so a request that crashed with an unhandled
            # exception never got a log line at all - the request/response
            # cycle just silently vanished from the logs. Log it as a
            # failure (with the real duration) before re-raising so FastAPI's
            # default handler can still convert it to a 500 response.
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "%s %s -> UNHANDLED EXCEPTION (%.1fms)",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
