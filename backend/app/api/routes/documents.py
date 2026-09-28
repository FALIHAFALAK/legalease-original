from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import client_key, get_current_user, rate_limiter, require_csrf
from app.db import get_db
from app.models import Document, DocumentVersion, Template, User
from app.providers.base import AIProviderError
from app.providers.factory import get_ai_provider
from app.schemas import (
    DocumentDetail,
    DocumentListResponse,
    DocumentUpdateRequest,
    GeneratedDocumentResponse,
    GenerateDocumentRequest,
    VersionResponse,
)
from app.services.documents import (
    DocumentServiceError,
    create_generated_document,
    document_detail,
    document_summary,
    duplicate_document,
    get_owned_document,
    update_document,
)
from app.services.exports import export_docx, export_pdf
from app.services.sanitizer import safe_filename

router = APIRouter(prefix="/api/documents", tags=["documents"])


def service_error(exc: DocumentServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    request: Request,
    q: str | None = Query(default=None, max_length=120),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentListResponse:
    query = (
        select(Document)
        .where(Document.user_id == user.id)
        .options(selectinload_document())
        .order_by(desc(Document.updated_at))
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(Document.title.ilike(term), Document.jurisdiction.ilike(term)))
    if status_filter:
        query = query.where(Document.status == status_filter)
    documents = list(db.scalars(query))
    return DocumentListResponse(
        items=[document_summary(item) for item in documents],
        total=len(documents),
        draft_count=sum(item.status == "draft" for item in documents),
        completed_count=sum(item.status in {"ready_for_review", "completed"} for item in documents),
    )


def selectinload_document():
    from sqlalchemy.orm import selectinload

    return selectinload(Document.template)


@router.post("/generate", response_model=GeneratedDocumentResponse, status_code=201)
def generate_document(
    payload: GenerateDocumentRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> GeneratedDocumentResponse:
    rate_limiter.check(client_key(request, "generate"), 20, 3600)
    template = db.scalar(
        select(Template).where(Template.slug == payload.template_slug, Template.is_active.is_(True))
    )
    if not template:
        raise HTTPException(
            status_code=404, detail={"code": "template_not_found", "message": "Template not found."}
        )
    try:
        provider = get_ai_provider()
        result = create_generated_document(
            db, user, template, payload.fields, payload.jurisdiction, provider
        )
    except DocumentServiceError as exc:
        raise service_error(exc) from exc
    except AIProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": getattr(exc, "code", "ai_unavailable"), "message": str(exc)},
        ) from exc
    return result


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DocumentDetail:
    try:
        document = get_owned_document(db, user, document_id)
    except DocumentServiceError as exc:
        raise service_error(exc) from exc
    return document_detail(document)


@router.patch("/{document_id}", response_model=DocumentDetail)
def save_document(
    document_id: int,
    payload: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> DocumentDetail:
    try:
        document = get_owned_document(db, user, document_id)
        updated = update_document(db, document, payload)
    except DocumentServiceError as exc:
        raise service_error(exc) from exc
    return document_detail(updated)


@router.post("/{document_id}/duplicate", response_model=DocumentDetail, status_code=201)
def duplicate_existing_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> DocumentDetail:
    try:
        document = duplicate_document(db, get_owned_document(db, user, document_id))
    except DocumentServiceError as exc:
        raise service_error(exc) from exc
    return document_detail(document)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> Response:
    try:
        document = get_owned_document(db, user, document_id)
    except DocumentServiceError as exc:
        raise service_error(exc) from exc
    db.delete(document)
    db.commit()
    return Response(status_code=204)


@router.get("/{document_id}/versions", response_model=list[VersionResponse])
def list_versions(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[VersionResponse]:
    try:
        document = get_owned_document(db, user, document_id)
    except DocumentServiceError as exc:
        raise service_error(exc) from exc
    versions = db.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document.id)
        .order_by(desc(DocumentVersion.version_number))
    )
    return [VersionResponse.model_validate(item) for item in versions]


@router.get("/{document_id}/export/{file_format}")
def export_document(
    document_id: int,
    file_format: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    try:
        document = get_owned_document(db, user, document_id)
    except DocumentServiceError as exc:
        raise service_error(exc) from exc
    if file_format not in {"pdf", "docx"}:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_format", "message": "Export format must be pdf or docx."},
        )
    if file_format == "pdf":
        content = export_pdf(document.title, document.content_html)
        media_type = "application/pdf"
    else:
        content = export_docx(document.title, document.content_html)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    filename = safe_filename(document.title, "legalease-document")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{file_format}"'},
    )
