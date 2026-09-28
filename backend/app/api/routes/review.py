from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.api.dependencies import client_key, get_current_user, rate_limiter, require_csrf
from app.config import settings
from app.db import get_db
from app.models import DocumentReview, User
from app.providers.base import AIProviderError, ProviderResponseError
from app.providers.factory import get_ai_provider
from app.schemas import (
    ComparisonResponse,
    FindingDetail,
    FindingQuestionRequest,
    FindingQuestionResponse,
    FindingStatusUpdate,
    ReanalyzeResponse,
    ReviewDetailResponse,
    ReviewListResponse,
    ReviewMessageResponse,
    ReviewResponse,
)
from app.services.clauses import ExtractedDocument
from app.services.disclaimers import (
    AUTOMATED_ANALYSIS_DISCLAIMER,
    CLAUSE_ANSWER_DISCLAIMER,
)
from app.services.exports import export_review_report
from app.services.review_intelligence import (
    ReviewServiceError,
    analyze_document,
    clause_text_for,
    comparison_for,
    finding_detail,
    finding_messages,
    finding_summary,
    get_owned_document,
    get_owned_finding,
    get_owned_review,
    latest_version,
    list_reviews,
    message_history,
    message_response,
    register_message,
    report_filename,
    review_findings,
    review_response,
    update_finding_status,
)
from app.services.reviews import FileValidationError, extract_upload, max_upload_bytes

router = APIRouter(prefix="/api/review", tags=["review"])


def service_error(exc: ReviewServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}
    )


def ai_error(exc: AIProviderError) -> HTTPException:
    code = getattr(exc, "code", "ai_unavailable")
    status_code = 504 if code == "ai_timeout" else 503
    return HTTPException(status_code=status_code, detail={"code": code, "message": str(exc)})


async def read_upload(file: UploadFile) -> ExtractedDocument:
    """Validate and extract an upload on the server before any analysis runs."""

    data = await file.read(max_upload_bytes() + 1)
    try:
        return extract_upload(file.filename or "", file.content_type, data)
    except FileValidationError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "invalid_upload", "message": str(exc)}
        ) from exc


def _review_payload(db: Session, review: DocumentReview) -> ReviewResponse:
    return review_response(db, review)


def _detail_payload(
    db: Session, review: DocumentReview, comparison: ComparisonResponse | None = None
) -> ReviewDetailResponse:
    payload = review_response(db, review)
    return ReviewDetailResponse(
        **payload.model_dump(),
        comparison=comparison or comparison_for(db, review, review_findings(db, review.id)),
    )


async def _run_review(
    request: Request,
    file: UploadFile,
    document_id: int | None,
    previous_review_id: int | None,
    db: Session,
    user: User,
) -> ReviewResponse:
    rate_limiter.check(client_key(request, "review"), 12, 3600)
    document = None
    if document_id is not None:
        try:
            document = get_owned_document(db, user, document_id)
        except ReviewServiceError as exc:
            raise service_error(exc) from exc
    previous_review = None
    if previous_review_id is not None:
        try:
            previous_review = get_owned_review(db, user, previous_review_id)
        except ReviewServiceError as exc:
            raise service_error(exc) from exc
        if document is None and previous_review.document_id is not None:
            try:
                document = get_owned_document(db, user, previous_review.document_id)
            except ReviewServiceError as exc:
                raise service_error(exc) from exc
    extracted = await read_upload(file)
    try:
        review, clauses, _comparison = analyze_document(
            db,
            user,
            get_ai_provider(),
            document,
            extracted,
            file.filename or "uploaded document",
            previous_review,
        )
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    except ProviderResponseError as exc:
        db.rollback()
        raise HTTPException(
            status_code=502, detail={"code": "invalid_ai_response", "message": str(exc)}
        ) from exc
    except AIProviderError as exc:
        raise ai_error(exc) from exc
    return _review_payload(db, review)


@router.post("", response_model=ReviewResponse)
async def create_review(
    request: Request,
    file: UploadFile = File(...),
    document_id: int | None = Form(default=None),
    previous_review_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ReviewResponse:
    """Analyse an uploaded document at clause level and persist every finding."""

    return await _run_review(request, file, document_id, previous_review_id, db, user)


@router.post("/analyse", response_model=ReviewResponse, status_code=201)
async def create_review_alias(
    request: Request,
    file: UploadFile = File(...),
    document_id: int | None = Form(default=None),
    previous_review_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ReviewResponse:
    """Alias kept so existing clients posting to /api/review/analyse keep working."""

    return await _run_review(request, file, document_id, previous_review_id, db, user)



@router.get("", response_model=ReviewListResponse)
def list_user_reviews(
    document_id: int | None = Query(default=None, alias="document_id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReviewListResponse:
    items, counts = list_reviews(db, user, document_id)
    return ReviewListResponse(items=items, total=len(items), counts=counts)



@router.get("/disclaimer")
def disclaimer() -> dict[str, str]:
    """Expose the automated-analysis disclaimer so the frontend never drifts from it."""

    return {"disclaimer": AUTOMATED_ANALYSIS_DISCLAIMER}


@router.get("/{review_id}", response_model=ReviewDetailResponse)
def get_review(
    review_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ReviewDetailResponse:
    try:
        review = get_owned_review(db, user, review_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    return _detail_payload(db, review)


@router.delete("/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> Response:
    try:
        review = get_owned_review(db, user, review_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    db.delete(review)
    db.commit()
    return Response(status_code=204)


@router.get("/{review_id}/comparison", response_model=ComparisonResponse)
def get_comparison(
    review_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ComparisonResponse:
    try:
        review = get_owned_review(db, user, review_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    return comparison_for(db, review, review_findings(db, review.id))


@router.post("/{review_id}/reanalyze", response_model=ReanalyzeResponse)
async def reanalyze_latest_version(
    request: Request,
    review_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ReanalyzeResponse:
    """Re-run analysis against the latest stored version of the reviewed document."""

    rate_limiter.check(client_key(request, "reanalyze"), 12, 3600)
    try:
        review = get_owned_review(db, user, review_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    if review.document_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "document_required",
                "message": "Link this review to a saved document before re-analysing a version.",
            },
        )
    try:
        document = get_owned_document(db, user, review.document_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    version = latest_version(db, document.id)
    if version is None or not version.content_text.strip():
        raise HTTPException(
            status_code=409,
            detail={
                "code": "no_version_text",
                "message": "The latest document version has no stored text to analyse.",
            },
        )
    extracted = ExtractedDocument(
        file_type=version.file_type or "txt",
        text=version.content_text,
        pages=list(version.pages or []),
        page_reference_kind=version.page_reference_kind,
    )
    filename = version.source_filename or f"{document.title}.txt"
    try:
        new_review, clauses, comparison = analyze_document(
            db, user, get_ai_provider(), document, extracted, filename, review
        )
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    except ProviderResponseError as exc:
        db.rollback()
        raise HTTPException(
            status_code=502, detail={"code": "invalid_ai_response", "message": str(exc)}
        ) from exc
    except AIProviderError as exc:
        raise ai_error(exc) from exc
    return ReanalyzeResponse(review=_review_payload(db, new_review), comparison=comparison)


@router.get("/{review_id}/report")
def download_report(
    review_id: int,
    include_resolved: bool = Query(default=True),
    include_questions: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Export the clause review, findings, and outstanding questions as a PDF report."""

    try:
        review = get_owned_review(db, user, review_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    findings = review_findings(db, review.id)
    payload = review_response(db, review)
    comparison = comparison_for(db, review, findings)
    content = export_review_report(
        review=review,
        findings=findings,
        clauses=payload.clauses,
        comparison=comparison,
        messages_by_finding={
            finding.id: finding_messages(db, finding.id) for finding in findings
        },
        include_resolved=include_resolved,
        include_questions=include_questions,
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report_filename(review)}.pdf"',
            "Cache-Control": "no-store, private",
        },
    )


@router.patch("/findings/{finding_id}", response_model=FindingDetail)
def set_finding_status(
    finding_id: int,
    payload: FindingStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> FindingDetail:
    try:
        finding = get_owned_finding(db, user, finding_id)
        update_finding_status(db, finding, payload.status, payload.note, payload.evidence)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    return finding_detail(finding)


@router.get("/findings/{finding_id}", response_model=FindingDetail)
def get_finding(
    finding_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> FindingDetail:
    try:
        finding = get_owned_finding(db, user, finding_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    return finding_detail(finding)


@router.get("/findings/{finding_id}/questions", response_model=list[ReviewMessageResponse])
def list_finding_questions(
    finding_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ReviewMessageResponse]:
    try:
        finding = get_owned_finding(db, user, finding_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    return [message_response(item) for item in finding_messages(db, finding.id)]


@router.post("/findings/{finding_id}/questions", response_model=FindingQuestionResponse)
def ask_finding_question(
    request: Request,
    finding_id: int,
    payload: FindingQuestionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> FindingQuestionResponse:
    """Answer a question about one finding, optionally with a suggested revision."""

    rate_limiter.check(client_key(request, "review-question"), settings.max_review_questions_per_hour, 3600)
    try:
        finding = get_owned_finding(db, user, finding_id)
    except ReviewServiceError as exc:
        raise service_error(exc) from exc
    history_rows = finding_messages(db, finding.id)
    question = register_message(
        db, finding, role="user", kind="question", content=payload.question.strip()
    )
    provider = get_ai_provider()
    payload_for_model: dict[str, Any] = finding_summary(finding).model_dump()
    try:
        result = provider.answer_finding_question(
            payload_for_model,
            payload.question.strip(),
            clause_text_for(finding),
            message_history(history_rows),
            payload.request_revision,
        )
    except AIProviderError as exc:
        db.rollback()
        raise ai_error(exc) from exc
    answer = str(result.data.get("answer") or "").strip()
    if not answer:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail={
                "code": "invalid_ai_response",
                "message": "The AI provider returned an empty answer for this question.",
            },
        )
    revision = str(result.data.get("suggested_revision") or "").strip()
    kind = "suggested_revision" if payload.request_revision else "explanation"
    answer_row = register_message(
        db,
        finding,
        role="assistant",
        kind=kind,
        content=answer,
        suggested_revision=revision,
        provider=result.provider,
        model=result.model,
    )
    db.commit()
    db.refresh(answer_row)
    return FindingQuestionResponse(
        finding_id=finding.id,
        question_id=question.id,
        answer_id=answer_row.id,
        question=question.content,
        answer=answer,
        suggested_revision=revision,
        suggested_wording=finding.suggested_wording,
        disclaimer=CLAUSE_ANSWER_DISCLAIMER,
        provider=result.provider,
        model=result.model,
        messages=[message_response(item) for item in finding_messages(db, finding.id)],
        created_at=answer_row.created_at,
    )
