"""Minimal in-process sliding-window rate limiter.

Deliberately not a distributed limiter (no Redis) — this app runs as a single
uvicorn worker (see backend/Dockerfile's prod CMD), so in-memory state is
correct for the current deployment shape. If this ever runs with multiple
workers/instances behind a load balancer, this needs to move to a shared
store (Redis) instead, since each process would otherwise track its own
independent counters.
"""

import threading
import time
from collections import defaultdict

from starlette.requests import Request

_lock = threading.Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """The backend is only ever reached through nginx (see docker-compose.yml —
    it has no published port of its own), which always sets X-Real-IP to the
    real connecting client's address (nginx.conf's `proxy_set_header X-Real-IP
    $remote_addr`). Without this, request.client.host would always resolve to
    nginx's own container IP, making any per-IP limit effectively global
    across every real user instead of per-client."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


def check_rate_limit(key: str, *, max_requests: int, window_seconds: float) -> bool:
    """Returns True if this request is allowed under `key`'s sliding window,
    False if the limit has already been reached (caller should reject)."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        timestamps = _hits[key]
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
        return True


def reset_rate_limits() -> None:
    """Test-only: clears all tracked state between test cases."""
    with _lock:
        _hits.clear()
