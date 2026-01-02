import os
import time
import threading
from typing import Tuple

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token, AuthTokenError


bearer = HTTPBearer(auto_error=False)


class FixedWindowLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, Tuple[int, int]] = {}

    def allow(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        now = int(time.time())
        window_start = now - (now % window_seconds)
        with self._lock:
            current = self._state.get(key)
            if current is None or current[0] != window_start:
                self._state[key] = (window_start, 1)
                return True, window_seconds - (now - window_start)
            count = current[1]
            if count >= limit:
                return False, window_seconds - (now - window_start)
            self._state[key] = (window_start, count + 1)
            return True, window_seconds - (now - window_start)


_limiter = FixedWindowLimiter()


def _enabled() -> bool:
    return os.getenv("HUBEX_RL_ENABLED", "0") == "1"


def _limit_per_minute() -> int:
    try:
        return max(1, int(os.getenv("HUBEX_RL_PER_MIN", "60")))
    except ValueError:
        return 60


async def rate_limit_guard(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> None:
    if not _enabled():
        return

    if not creds or not creds.credentials:
        return

    try:
        payload = decode_access_token(creds.credentials)
    except AuthTokenError:
        return
    except Exception:
        return

    subject = payload.get("sub")
    if not subject:
        return

    method = request.method.upper()
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    key = f"{subject}:{method}:{path}"

    limit = _limit_per_minute()
    ok, retry_after = _limiter.allow(key, limit, 60)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail="rate_limited",
            headers={"Retry-After": str(max(1, retry_after))},
        )
