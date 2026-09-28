from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.security import csrf_matches, read_session_token


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            events = [item for item in self._events[key] if item > now - window_seconds]
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "rate_limited",
                        "message": "Too many requests. Please try again shortly.",
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)
            self._events[key] = events[-limit:]

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


rate_limiter = RateLimiter()


def client_key(request: Request, suffix: str = "") -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    address = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    return f"{address}:{suffix}"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    user_id = read_session_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "Please sign in to continue."},
        )
    return user


def require_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    expected = request.cookies.get(settings.csrf_cookie_name)
    candidate = request.headers.get("x-csrf-token")
    if not csrf_matches(candidate, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "csrf_failed", "message": "Request protection could not be verified."},
        )


def require_admin(user: User) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "admin_required", "message": "Administrator access is required."},
        )
    return user
