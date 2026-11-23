"""Per-IP rate limit for the credential endpoints (/auth/login, /auth/register).

An in-process sliding window: it needs no extra service, but each API process counts on its own,
so with N workers the effective limit is N times higher. It resets when the process restarts.
Time comes from `clock`, which tests replace (or call `reset()`), so no test has to sleep.
"""
import math
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

DEFAULT_AUTH_RATE_LIMIT = 5
DEFAULT_AUTH_RATE_WINDOW_SECONDS = 60

# Replaced in tests with a fake clock; must return seconds as a float.
clock = time.monotonic

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1:
        raise RuntimeError(f"{name} must be a positive integer, got {raw!r}.")
    return value


def reset() -> None:
    """Forget all counters (used by the test suite between tests)."""
    with _lock:
        _hits.clear()


def client_ip(request: Request) -> str:
    """The caller's IP. X-Forwarded-For is only read when TRUST_PROXY_HEADERS=1.

    Each proxy appends the address it saw to the right of the header, so entries further left can
    be forged by the client. We take the entry TRUSTED_PROXY_HOPS places from the right
    (default 1: the address the first proxy in front of the API saw).
    """
    peer = request.client.host if request.client else "unknown"
    if os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return peer
    forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    hops = _env_positive_int("TRUSTED_PROXY_HOPS", 1)
    if len(forwarded) >= hops:
        return forwarded[-hops]
    return peer


def limit_auth_attempts(request: Request) -> None:
    """Dependency: 429 once one IP exceeds the allowed attempts per window on this route."""
    limit = _env_positive_int("AUTH_RATE_LIMIT", DEFAULT_AUTH_RATE_LIMIT)
    window = _env_positive_int("AUTH_RATE_WINDOW_SECONDS", DEFAULT_AUTH_RATE_WINDOW_SECONDS)
    key = (request.url.path, client_ip(request))
    now = clock()
    with _lock:
        hits = _hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, math.ceil(hits[0] + window - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Please wait {retry_after} seconds and try again.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        if len(_hits) > 10_000:  # bound memory: drop keys whose window has fully passed
            for k in [k for k, v in _hits.items() if not v or v[-1] <= now - window]:
                del _hits[k]
