import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB


def _client_ip(request: Request) -> str:
    # 1. Cloudflare real visitor IP
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    # 2. Behind nginx / reverse proxy we trust the first X-Forwarded-For hop.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # 3. Direct connection
    return request.client.host if request.client else "unknown"


class UploadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized requests before the body is fully read.

    Coarse first line of defence: multipart requests carry boundary/field
    overhead on top of the file bytes. The exact per-file limit is enforced
    while streaming the upload to disk in ``app.utils``.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > MAX_UPLOAD_SIZE_BYTES + (2 * 1024 * 1024):
                        return JSONResponse(
                            status_code=413,
                            content={"detail": f"Arquivo excede o limite de {MAX_UPLOAD_SIZE_MB} MB."},
                        )
                except ValueError:
                    pass
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-IP fixed-window rate limiter for conversion requests (POST).

    Configured via env: RATE_LIMIT_REQUESTS (default 60) per
    RATE_LIMIT_WINDOW_SECONDS (default 60). Only mutating requests are counted
    so job-status polling and static assets are unaffected.
    """

    def __init__(self, app, *, requests: int | None = None, window_seconds: int | None = None):
        super().__init__(app)
        self.requests = requests if requests is not None else self._env_int("RATE_LIMIT_REQUESTS", 60)
        self.window_seconds = window_seconds if window_seconds is not None else self._env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_prune = time.monotonic()

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        try:
            return int(os.environ.get(name, default))
        except (TypeError, ValueError):
            return default

    def _prune(self, now: float) -> None:
        if now - self._last_prune < self.window_seconds:
            return
        self._last_prune = now
        for key, dq in list(self._hits.items()):
            while dq and dq[0] <= now - self.window_seconds:
                dq.popleft()
            if not dq:
                self._hits.pop(key, None)

    async def dispatch(self, request: Request, call_next):
        if request.method != "POST":
            return await call_next(request)

        now = time.monotonic()
        key = _client_ip(request)
        with self._lock:
            dq = self._hits[key]
            while dq and dq[0] <= now - self.window_seconds:
                dq.popleft()
            if len(dq) >= self.requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Muitas requisições. Tente novamente em instantes."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
            dq.append(now)
        self._prune(now)
        return await call_next(request)
