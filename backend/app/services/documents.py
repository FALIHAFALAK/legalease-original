from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentVersion, Template, UsageRecord, User
from app.providers.base import AIProviderError
from app.schemas import (
    DocumentDetail,
    DocumentMetadata,
    DocumentSummary,
    DocumentUpdateRequest,
    GeneratedDocumentResponse,
)
from app.services.sanitizer import html_to_text, sanitize_html


class DocumentServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def template_to_dict(template: Template) -> dict[str, Any]:
    return {
        "slug": template.slug,
        "name": template.name,
        "sections": template.sections or [],
        "fields": template.fields or [],
        "generation_instructions": template.generation_instructions,
    }


def validate_form_data(template: Template, values: dict[str, Any]) -> dict[str, Any]:
    definitions = {item["name"]: item for item in (template.fields or [])}
    unknown = set(values) - set(definitions)
    if unknown:
        raise DocumentServiceError(
            422, "unknown_fields", "The form contains fields that are not part of this template."
        )
    normalized: dict[str, Any] = {}
    missing: list[str] = []
    for name, definition in definitions.items():
        value = values.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            value = None
        if definition.get("required") and value is None:
            missing.append(definition.get("label", name))
        if value is not None:
            if not isinstance(value, (str, int, float, bool)):
                raise DocumentServiceError(
                    422, "invalid_field", f"The field {name} must be a simple value."
                )
            text = str(value).strip()
            if len(text) > 4000:
                raise DocumentServiceError(422, "field_too_long", f"The field {name} is too long.")
            if definition.get("type") == "select" and text not in definition.get("options", []):
                raise DocumentServiceError(
                    422,
                    "invalid_option",
                    f"Choose a valid option for {definition.get('label', name)}.",
                )
            normalized[name] = text
    if missing:
        raise DocumentServiceError(
            422, "missing_fields", f"Complete the required fields: {', '.join(missing)}."
        )
    return normalized


def _validate_ai_document(
    data: dict[str, Any], template: Template, jurisdiction: str | None, fallback_title: str
) -> DocumentMetadata:
    if not isinstance(data.get("title"), str) or not data.get("content"):
        raise DocumentServiceError(
            502, "invalid_ai_response", "The AI provider returned an incomplete document draft."
        )
    try:
        metadata = DocumentMetadata(
            title=(data.get("title") or fallback_title)[:240],
            content=sanitize_html(str(data.get("content"))),
            sections=[
                str(item)[:200] for item in (data.get("sections") or template.sections or [])
            ][:50],
            jurisdiction=str(data.get("jurisdiction") or jurisdiction or "Not specified")[:120],
            missing_information=[
                str(item)[:300] for item in (data.get("missing_information") or [])
            ][:30],
            assumptions=[str(item)[:300] for item in (data.get("assumptions") or [])][:30],
            review_notes=[str(item)[:300] for item in (data.get("review_notes") or [])][:30],
        )
    except Exception as exc:
        raise DocumentServiceError(
            502, "invalid_ai_response", "The AI provider response could not be validated."
        ) from exc
    if not metadata.content.strip():
        raise DocumentServiceError(
            502, "invalid_ai_response", "The AI provider returned an empty document."
        )
    return metadata


def create_generated_document(
    db: Session,
    user: User,
    template: Template,
    values: dict[str, Any],
    jurisdiction: str | None,
    provider: Any,
) -> GeneratedDocumentResponse:
    normalized = validate_form_data(template, values)
    input_size = sum(len(str(value)) for value in normalized.values())
    try:
        result = provider.generate_document(template_to_dict(template), normalized, jurisdiction)
    except AIProviderError as exc:
        db.add(
            UsageRecord(
                user_id=user.id,
                operation="generate",
                provider=getattr(provider, "name", "unknown"),
                input_characters=input_size,
                success=False,
                error_code=getattr(exc, "code", "ai_error"),
            )
        )
        db.commit()
        raise DocumentServiceError(502, getattr(exc, "code", "ai_error"), str(exc)) from exc
    metadata = _validate_ai_document(result.data, template, jurisdiction, template.name)
    document = Document(
        user_id=user.id,
        template_id=template.id,
        title=metadata.title,
        status="draft",
        jurisdiction=metadata.jurisdiction,
        content_html=metadata.content,
        content_text=html_to_text(metadata.content),
        form_data=normalized,
        missing_information=metadata.missing_information,
        assumptions=metadata.assumptions,
        review_notes=metadata.review_notes,
        current_version=1,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentVersion(
            document_id=document.id,
            version_number=1,
            title=document.title,
            content_html=document.content_html,
            content_text=document.content_text,
            change_note="Initial AI-assisted draft",
        )
    )
    db.add(
        UsageRecord(
            user_id=user.id,
            operation="generate",
            provider=result.provider,
            input_characters=input_size,
            success=True,
        )
    )
    db.commit()
    db.refresh(document)
    return GeneratedDocumentResponse(
        document=DocumentMetadata(
            title=metadata.title,
            content=metadata.content,
            sections=metadata.sections,
            jurisdiction=metadata.jurisdiction,
            missing_information=metadata.missing_information,
            assumptions=metadata.assumptions,
            review_notes=metadata.review_notes,
        ),
        document_id=document.id,
        provider=result.provider,
        model=result.model,
        is_draft=True,
    )


def get_owned_document(db: Session, user: User, document_id: int) -> Document:
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise DocumentServiceError(404, "document_not_found", "Document not found.")
    return document


def document_summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        status=document.status,
        jurisdiction=document.jurisdiction,
        template_slug=document.template.slug if document.template else None,
        updated_at=document.updated_at,
        created_at=document.created_at,
        current_version=document.current_version,
    )


def document_detail(document: Document) -> DocumentDetail:
    return DocumentDetail(
        id=document.id,
        title=document.title,
        status=document.status,
        jurisdiction=document.jurisdiction,
        template_slug=document.template.slug if document.template else None,
        updated_at=document.updated_at,
        created_at=document.created_at,
        current_version=document.current_version,
        content_html=document.content_html,
        content_text=document.content_text,
        form_data=document.form_data or {},
        missing_information=document.missing_information or [],
        assumptions=document.assumptions or [],
        review_notes=document.review_notes or [],
    )


def update_document(db: Session, document: Document, payload: DocumentUpdateRequest) -> Document:
    changed = False
    if payload.title is not None and payload.title != document.title:
        document.title = payload.title
        changed = True
    if payload.status is not None and payload.status != document.status:
        document.status = payload.status
        changed = True
    if payload.content_html is not None:
        cleaned = sanitize_html(payload.content_html)
        if not cleaned.strip():
            raise DocumentServiceError(422, "empty_document", "Document content cannot be empty.")
        if cleaned != document.content_html:
            document.content_html = cleaned
            document.content_text = html_to_text(cleaned)
            changed = True
    elif payload.content_text is not None and payload.content_text != document.content_text:
        document.content_text = payload.content_text[:200000]
        changed = True
    if changed:
        document.current_version += 1
        db.add(
            DocumentVersion(
                document_id=document.id,
                version_number=document.current_version,
                title=document.title,
                content_html=document.content_html,
                content_text=document.content_text,
                change_note=payload.change_note or "Saved edit",
            )
        )
    db.commit()
    db.refresh(document)
    return document


def duplicate_document(db: Session, document: Document) -> Document:
    duplicate = Document(
        user_id=document.user_id,
        template_id=document.template_id,
        title=f"{document.title} (copy)"[:240],
        status="draft",
        jurisdiction=document.jurisdiction,
        content_html=document.content_html,
        content_text=document.content_text,
        form_data=dict(document.form_data or {}),
        missing_information=list(document.missing_information or []),
        assumptions=list(document.assumptions or []),
        review_notes=list(document.review_notes or []),
        current_version=1,
    )
    db.add(duplicate)
    db.flush()
    db.add(
        DocumentVersion(
            document_id=duplicate.id,
            version_number=1,
            title=duplicate.title,
            content_html=duplicate.content_html,
            content_text=duplicate.content_text,
            change_note="Duplicated document",
        )
    )
    db.commit()
    db.refresh(duplicate)
    return duplicate
