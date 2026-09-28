from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIMessage, Conversation, Document, User
from app.providers.base import AIProviderError, ProviderResponseError
from app.schemas import AssistantResponse
from app.services.sanitizer import html_to_text

ASSISTANT_DISCLAIMER = (
    "General legal information only, not legal advice. Laws and procedures vary by jurisdiction; "
    "consult a qualified lawyer about your specific situation."
)


def get_owned_conversation(db: Session, user: User, conversation_id: int) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    if conversation is None:
        raise ValueError("Conversation not found.")
    return conversation


def ask_assistant(
    db: Session,
    user: User,
    provider,
    message: str,
    conversation_id: int | None = None,
    document_id: int | None = None,
) -> AssistantResponse:
    question = message.strip()
    if not question:
        raise ValueError("Enter a legal question before sending it to the assistant.")

    conversation: Conversation | None = None
    if conversation_id is not None:
        try:
            conversation = get_owned_conversation(db, user, conversation_id)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
    context = ""
    if document_id is not None:
        document = db.scalar(
            select(Document).where(Document.id == document_id, Document.user_id == user.id)
        )
        if document is None:
            raise ValueError("Document not found.")
        context = html_to_text(document.content_html)[:30000]
    if conversation is None:
        conversation = Conversation(
            user_id=user.id, title=question[:80] or "New conversation"
        )
        db.add(conversation)
        db.flush()
    db.add(AIMessage(conversation_id=conversation.id, role="user", content=question))
    history_items = list(
        db.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation.id)
            .order_by(AIMessage.id.desc())
            .limit(8)
        )
    )
    history = [
        {"role": item.role, "content": item.content[:2000]}
        for item in reversed(history_items)
    ]
    try:
        result = provider.answer_question(question, context, history)
    except AIProviderError:
        db.rollback()
        raise
    raw_answer = result.data.get("answer") if isinstance(result.data, dict) else None
    answer = raw_answer.strip() if isinstance(raw_answer, str) else ""
    if not answer:
        db.rollback()
        raise ProviderResponseError("The AI provider returned an empty or invalid answer.")
    assistant_message = AIMessage(
        conversation_id=conversation.id, role="assistant", content=answer[:20000]
    )
    db.add(assistant_message)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_message)
    return AssistantResponse(
        conversation_id=conversation.id,
        message=answer[:20000],
        disclaimer=ASSISTANT_DISCLAIMER,
        provider=result.provider,
        model=result.model,
        created_at=assistant_message.created_at,
    )
