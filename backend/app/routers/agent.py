from __future__ import annotations

import time
from collections import deque, defaultdict
from typing import Deque, Dict

from fastapi import APIRouter, Request, HTTPException, status

from app.agent import generate_answer
from app.schemas import AgentChatRequest, AgentChatResponse


router = APIRouter(prefix="/agent", tags=["agent"])

# Simple in-memory rate limiter: 60 requests per minute per key
WINDOW_SECONDS = 60
MAX_REQUESTS = 60
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _rate_limit_key(request: Request) -> str:
    # Prefer session id header if provided, else client IP
    sid = request.headers.get("x-session-id")
    if sid:
        return f"sid:{sid}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def _enforce_rate_limit(key: str) -> None:
    now = time.time()
    dq = _hits[key]
    dq.append(now)
    # prune window
    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()
    if len(dq) > MAX_REQUESTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")


@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(request: Request, payload: AgentChatRequest) -> AgentChatResponse:
    _enforce_rate_limit(_rate_limit_key(request))
    # Pass through optional conversation context for better responses
    context = payload.context or []
    # Normalize context: only keep role/content
    norm_ctx = []
    for m in context[-10:]:
        role = str(m.get("role", "")).lower()
        content = str(m.get("content", ""))
        if role in {"user", "assistant"} and content:
            norm_ctx.append({"role": role, "content": content})
    return generate_answer(payload.message, norm_ctx)


