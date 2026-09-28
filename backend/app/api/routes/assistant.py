from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.dependencies import client_key, get_current_user, rate_limiter, require_csrf
from app.db import get_db
from app.models import Conversation, User
from app.providers.base import AIProviderError
from app.providers.factory import get_ai_provider
from app.schemas import (
    AssistantRequest,
    AssistantResponse,
    ConversationDetail,
    ConversationSummary,
    MessageResponse,
)
from app.services.assistant import ask_assistant, get_owned_conversation

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantResponse)
def chat(
    payload: AssistantRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> AssistantResponse:
    rate_limiter.check(client_key(request, "assistant"), 40, 3600)
    try:
        provider = get_ai_provider()
        return ask_assistant(
            db,
            user,
            provider,
            payload.message.strip(),
            payload.conversation_id,
            payload.document_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "assistant_error", "message": str(exc)}
        ) from exc
    except AIProviderError as exc:
        code = getattr(exc, "code", "ai_unavailable")
        status_code = 504 if code == "ai_timeout" else 503
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": str(exc)},
        ) from exc


@router.get("/conversations", response_model=list[ConversationSummary])
def conversations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ConversationSummary]:
    items = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(desc(Conversation.updated_at))
    )
    return [ConversationSummary.model_validate(item) for item in items]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def conversation_detail(
    conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ConversationDetail:
    try:
        conversation = get_owned_conversation(db, user, conversation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail={"code": "conversation_not_found", "message": str(exc)}
        ) from exc
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse.model_validate(item) for item in conversation.messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> None:
    try:
        conversation = get_owned_conversation(db, user, conversation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail={"code": "conversation_not_found", "message": str(exc)}
        ) from exc
    db.delete(conversation)
    db.commit()
    return None
