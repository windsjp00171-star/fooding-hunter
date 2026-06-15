"""
Minimal in-memory sliding-window rate limiter.

Pragmatic defense against a single user/IP hammering endpoints that can trigger
the Places API or flood Supabase. Keyed by logged-in user_id, falling back to
remote IP. State is per-process (resets on restart and is not shared across
gunicorn workers) — the hard backstop for API spend is the GCP budget cap.
"""
import time
from collections import defaultdict, deque
from functools import wraps

from flask import session, request, redirect, url_for

_hits: dict[str, deque] = defaultdict(deque)


def _client_key() -> str:
    uid = session.get('user_id')
    if uid:
        return f"u:{uid}"
    return f"ip:{request.headers.get('X-Forwarded-For', request.remote_addr or '?').split(',')[0].strip()}"


def rate_limit(max_calls: int, per_seconds: int):
    """Allow at most `max_calls` per `per_seconds` window per client."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f"{f.__name__}:{_client_key()}"
            now = time.monotonic()
            q = _hits[key]
            cutoff = now - per_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= max_calls:
                return '請慢一點，獵人。稍候片刻再試。', 429
            q.append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator
