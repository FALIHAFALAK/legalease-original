from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    FINDING_STATUSES,
    Document,
    DocumentReview,
    DocumentVersion,
    ReviewFinding,
    ReviewMessage,
    UsageRecord,
    User,
)
from app.providers.base import AIProviderError, ProviderResponseError
from app.schemas import (
    ClauseReference,
    ComparisonItem,
    ComparisonResponse,
    FindingDetail,
    FindingSummary,
    ReviewCounts,
    ReviewListItem,
    ReviewMessageResponse,
    ReviewResponse,
)
from app.schemas import (
    ReviewFinding as ReviewFindingSchema,
)
from app.services.clauses import (
    ExtractedDocument,
    find_quote_offset,
    find_quote_span,
    quote_still_present,
    segment_clauses,
)
from app.services.comparison import (
    MATCH_THRESHOLD,
    OUTCOME_CARRIED_OVER,
    OUTCOME_FIXED,
    OUTCOME_NEW,
    OUTCOME_UNRESOLVED,
    coerce_confidence,
    finding_signature,
    normalize_category,
    normalize_severity,
    sanitize_outcome,
    similarity,
)
from app.services.disclaimers import AUTOMATED_ANALYSIS_DISCLAIMER, PROFESSIONAL_REVIEW_NOTICE
from app.services.sanitizer import escape_text, safe_filename

FINDING_TEXT_LIMITS = {
    "title": 240,
    "clause_heading": 240,
    "clause_text": 8000,
    "excerpt": 1200,
    "explanation": 4000,
    "severity_explanation": 2000,
    "suggested_wording": 4000,
    "suggested_question": 1000,
}
EVIDENCE_LIMIT = 4000
SUMMARY_LIMIT = 6000
HISTORY_TURNS = 10
STORED_TEXT_LIMIT = 200000

# A "fixed" outcome is only accepted when it points at real wording in the new document.
# Without that evidence a concern is carried forward, so nothing is ever treated as
# resolved on the strength of the model saying so.
MIN_FIXED_EVIDENCE_CHARS = 25
MIN_CURRENT_MATCH_SCORE = 0.25


class ReviewServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _clip(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", "ignore")).hexdigest()


def clause_payloads(clauses: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "index": clause.index,
            "heading": clause.heading,
            "page_start": clause.page_start,
            "page_end": clause.page_end,
            "page_reference_kind": clause.page_reference_kind,
            "text": clause.text,
        }
        for clause in clauses
    ]


def citation_for(finding: ReviewFinding) -> str:
    if finding.page_start == finding.page_end:
        page = f"Page {finding.page_start}"
    else:
        page = f"Pages {finding.page_start}-{finding.page_end}"
    return f"{finding.clause_heading} ({page})" if finding.clause_heading else page


# --------------------------------------------------------------------------- ownership


def get_owned_review(db: Session, user: User, review_id: int) -> DocumentReview:
    review = db.scalar(
        select(DocumentReview).where(
            DocumentReview.id == review_id, DocumentReview.user_id == user.id
        )
    )
    if review is None:
        raise ReviewServiceError(404, "review_not_found", "Review not found.")
    return review


def get_owned_finding(db: Session, user: User, finding_id: int) -> ReviewFinding:
    finding = db.scalar(
        select(ReviewFinding).where(
            ReviewFinding.id == finding_id, ReviewFinding.user_id == user.id
        )
    )
    if finding is None:
        raise ReviewServiceError(404, "finding_not_found", "Finding not found.")
    return finding


def get_owned_document(db: Session, user: User, document_id: int) -> Document:
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise ReviewServiceError(404, "document_not_found", "Document not found.")
    return document


def latest_version(db: Session, document_id: int) -> DocumentVersion | None:
    return db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )


def latest_review(db: Session, document_id: int) -> DocumentReview | None:
    return db.scalar(
        select(DocumentReview)
        .where(DocumentReview.document_id == document_id, DocumentReview.status == "completed")
        .order_by(DocumentReview.id.desc())
        .limit(1)
    )


# --------------------------------------------------------------------------- analysis


def _record_usage(
    db: Session,
    user: User | int,
    operation: str,
    provider: str,
    input_characters: int,
    success: bool,
    error_code: str | None = None,
) -> None:
    db.add(
        UsageRecord(
            user_id=user.id if isinstance(user, User) else int(user),
            operation=operation,
            provider=provider[:32],
            input_characters=input_characters,
            success=success,
            error_code=error_code,
        )
    )


def review_findings(db: Session, review_id: int) -> list[ReviewFinding]:
    return list(
        db.scalars(
            select(ReviewFinding)
            .where(ReviewFinding.review_id == review_id)
            .order_by(ReviewFinding.id)
        )
    )


def _extract_quote(
    text: str, quote: str, clause_text: str = ""
) -> tuple[str, int, int]:
    """Resolve a quote to a span inside the clause text that is stored alongside it.

    The offsets are returned relative to ``clause_text`` so a consumer can highlight
    ``clause_text[quote_start_offset:quote_end_offset]`` directly. A quote the provider placed
    outside the clause it was attributed to resolves to an empty span rather than a misleading one.
    """

    cleaned = quote.strip()
    if not cleaned:
        return "", 0, 0
    if clause_text:
        local = find_quote_span(clause_text, cleaned)
        if local is not None:
            return cleaned, local[0], local[1]
    if find_quote_offset(text, cleaned) is None:
        return "", 0, 0
    return cleaned, 0, 0


def build_finding_values(
    item: dict[str, Any], clauses_by_index: dict[int, Any], text: str
) -> tuple[ReviewFinding, dict[str, Any]] | None:
    """Translate one provider finding into a persistable row plus its legacy JSON shape."""

    if not isinstance(item, dict):
        return None
    explanation = _clip(item.get("explanation"), FINDING_TEXT_LIMITS["explanation"])
    quote = str(item.get("quote") or "").strip()
    if not explanation or not quote or not clauses_by_index:
        return None
    try:
        clause_index = int(item.get("clause_index") or 0)
    except (TypeError, ValueError):
        clause_index = 0
    clause = clauses_by_index.get(clause_index)
    if clause is None:
        clause = clauses_by_index[sorted(clauses_by_index)[0]]

    quote, quote_start, quote_end = _extract_quote(text, quote, clause.text)

    finding = ReviewFinding(
        user_id=0,
        review_id=0,
        clause_index=clause.index,
        clause_heading=_clip(clause.heading, FINDING_TEXT_LIMITS["clause_heading"]),
        clause_text=_clip(clause.text, FINDING_TEXT_LIMITS["clause_text"]),
        excerpt=_clip(quote, FINDING_TEXT_LIMITS["excerpt"]),
        quote_start_offset=quote_start,
        quote_end_offset=quote_end,
        page_start=clause.page_start,
        page_end=clause.page_end,
        page_reference_kind=clause.page_reference_kind,
        category=normalize_category(item.get("category")),
        severity=normalize_severity(item.get("severity")),
        title=_clip(
            item.get("title") or clause.heading or f"Issue in clause {clause.index}",
            FINDING_TEXT_LIMITS["title"],
        ),
        explanation=explanation,
        severity_explanation=_clip(
            item.get("severity_explanation"), FINDING_TEXT_LIMITS["severity_explanation"]
        ),
        suggested_wording=_clip(
            item.get("suggested_wording"), FINDING_TEXT_LIMITS["suggested_wording"]
        ),
        suggested_question=_clip(
            item.get("suggested_question"), FINDING_TEXT_LIMITS["suggested_question"]
        ),
        confidence=coerce_confidence(item.get("confidence")),
        status="open",
        lifecycle="new",
        round_number=1,
    )
    legacy = {
        "category": finding.category,
        "severity": finding.severity,
        "excerpt": finding.excerpt,
        "explanation": finding.explanation,
        "suggested_question": finding.suggested_question,
    }
    return finding, legacy


def _persist_findings(
    db: Session,
    user: User,
    review: DocumentReview,
    items: list[Any],
    clauses: list[Any],
    text: str,
) -> list[ReviewFinding]:
    clauses_by_index = {clause.index: clause for clause in clauses}
    created: list[ReviewFinding] = []
    legacy: list[dict[str, Any]] = []
    for item in _as_list(items):
        if len(created) >= settings.max_findings_per_review:
            break
        built = build_finding_values(item, clauses_by_index, text)
        if built is None:
            continue
        finding, legacy_item = built
        finding.user_id = user.id
        finding.review_id = review.id
        finding.document_id = review.document_id
        finding.document_version_id = review.document_version_id
        finding.first_review_id = review.id
        finding.round_number = review.round_number
        finding.provider = review.provider
        finding.model = review.model
        db.add(finding)
        created.append(finding)
        legacy.append(legacy_item)
    review.findings = legacy
    return created


def _fallback_items(
    db: Session, user: User, review: DocumentReview, provider: Any, text: str
) -> list[dict[str, Any]]:
    """Keep the original document-level review usable when clause analysis finds nothing."""

    result = provider.review_document(text, review.filename)
    _record_usage(db, user, "review_document", result.provider, len(text), True)
    items: list[dict[str, Any]] = []
    for item in _as_list(result.data.get("findings")):
        if isinstance(item, dict):
            items.append(
                {
                    "clause_index": 0,
                    "quote": str(item.get("excerpt", "")),
                    "title": str(item.get("excerpt", ""))[:120] or "Document-level observation",
                    "category": item.get("category"),
                    "severity": item.get("severity"),
                    "explanation": item.get("explanation"),
                    "suggested_question": item.get("suggested_question"),
                }
            )
    review.summary = _clip(result.data.get("summary"), SUMMARY_LIMIT)
    return items


# --------------------------------------------------------------------------- comparison


def _best_current_match(
    previous_finding: ReviewFinding, remaining: list[ReviewFinding]
) -> tuple[ReviewFinding | None, float]:
    signature = finding_signature(previous_finding)
    best: ReviewFinding | None = None
    best_score = 0.0
    for finding in remaining:
        score = similarity(signature, finding_signature(finding))
        if finding.clause_index == previous_finding.clause_index:
            score += 0.15
        if score > best_score:
            best_score = score
            best = finding
    return best, best_score


def _has_cure_evidence(item: dict[str, Any], text: str, clauses_by_index: dict[int, Any]) -> bool:
    """Accept a "fixed" verdict only when the evidence points at real revised wording."""

    evidence = str(item.get("evidence") or "").strip()
    if len(evidence) < MIN_FIXED_EVIDENCE_CHARS:
        return False
    if find_quote_offset(text, " ".join(evidence.split()).strip('"“”\'')) is not None:
        return True
    try:
        clause_index = int(item.get("clause_index") or 0)
    except (TypeError, ValueError):
        clause_index = 0
    clause = clauses_by_index.get(clause_index)
    if clause is None:
        return False
    clause_words = {word.strip('.,;:"()').lower() for word in clause.text.split() if len(word) > 3}
    evidence_words = {word.strip('.,;:"()').lower() for word in evidence.split() if len(word) > 3}
    if not clause_words or not evidence_words:
        return False
    return len(clause_words & evidence_words) / len(evidence_words) >= 0.4


def _resolution_from_provider(
    raw_items: list[dict[str, Any]],
    by_previous: dict[int, ReviewFinding],
    created: list[ReviewFinding],
    text: str,
    clauses_by_index: dict[int, Any],
) -> dict[int, str]:
    resolution: dict[int, str] = {}
    claimed: set[int] = set()
    remaining = list(created)
    seen_previous: set[int] = set()
    for item in raw_items:
        try:
            previous_id = int(item.get("previous_finding_id"))
        except (TypeError, ValueError):
            previous_id = None
        if previous_id is None or previous_id in seen_previous:
            continue
        previous_finding = by_previous.get(previous_id)
        if previous_finding is None:
            continue
        seen_previous.add(previous_id)
        match, score = _best_current_match(previous_finding, remaining)
        if match is None or score < MIN_CURRENT_MATCH_SCORE:
            continue
        remaining.remove(match)
        outcome = sanitize_outcome(item.get("outcome")) or OUTCOME_UNRESOLVED
        if outcome == OUTCOME_FIXED and not _has_cure_evidence(item, text, clauses_by_index):
            outcome = OUTCOME_UNRESOLVED
        if outcome == OUTCOME_NEW:
            outcome = OUTCOME_UNRESOLVED
        match.previous_finding_id = previous_finding.id
        match.first_review_id = previous_finding.first_review_id or previous_finding.review_id
        match.lifecycle = outcome
        if outcome == OUTCOME_FIXED:
            match.resolution_evidence = _clip(item.get("evidence"), EVIDENCE_LIMIT)
        claimed.add(match.id)
        resolution[match.id] = outcome

    for item in raw_items:
        if item.get("previous_finding_id") is not None:
            continue
        try:
            clause_index = int(item.get("clause_index") or 0)
        except (TypeError, ValueError):
            clause_index = 0
        candidate = next(
            (
                finding
                for finding in remaining
                if finding.clause_index == clause_index and finding.id not in claimed
            ),
            None,
        )
        if candidate is None:
            candidate = next(
                (finding for finding in remaining if finding.id not in claimed), None
            )
        if candidate is None:
            continue
        candidate.title = _clip(item.get("title"), FINDING_TEXT_LIMITS["title"]) or candidate.title
        candidate.category = normalize_category(item.get("category") or candidate.category)
        candidate.severity = normalize_severity(item.get("severity") or candidate.severity)
        evidence = _clip(item.get("evidence"), 2000)
        if evidence:
            candidate.explanation = f"{candidate.explanation}\n\nEvidence from the revision: {evidence}".strip()
        candidate.lifecycle = OUTCOME_NEW
        claimed.add(candidate.id)
        resolution[candidate.id] = OUTCOME_NEW
    return resolution


def _resolution_from_text(
    previous_findings: list[ReviewFinding],
    created: list[ReviewFinding],
    text: str,
    clauses_by_index: dict[int, Any],
) -> dict[int, str]:
    """Provider-free fallback: keep a concern open unless the wording demonstrably changed."""

    resolution: dict[int, str] = {}
    remaining = list(created)
    for previous_finding in previous_findings:
        match, score = _best_current_match(previous_finding, remaining)
        if match is None or score < MATCH_THRESHOLD:
            continue
        remaining.remove(match)
        outcome = (
            OUTCOME_UNRESOLVED
            if find_quote_offset(text, previous_finding.excerpt) is not None
            else OUTCOME_FIXED
        )
        match.previous_finding_id = previous_finding.id
        match.first_review_id = previous_finding.first_review_id or previous_finding.review_id
        match.lifecycle = outcome
        if outcome == OUTCOME_FIXED:
            clause = clauses_by_index.get(match.clause_index)
            revised = (clause.text[:240] if clause else "").strip()
            match.resolution_evidence = (
                f'The wording flagged in the earlier version ("{previous_finding.excerpt[:200]}") '
                f"no longer appears in the revised document. The revised clause now reads: "
                f'"{revised}". A qualified lawyer should confirm the new wording covers the '
                "original concern."
            )
        resolution[match.id] = outcome
    return resolution


CLAUSE_UNCHANGED_SIMILARITY = 0.9


def _dropped_items(
    previous_findings: list[ReviewFinding],
    created: list[ReviewFinding],
    text: str,
    clauses_by_index: dict[int, Any],
) -> list[ComparisonItem]:
    """Report earlier concerns that the revision no longer raises.

    The trigger for calling a concern fixed is that the clause carrying it was rewritten and
    the revised analysis did not re-raise it. Quoted wording alone is not enough, because a
    cure is often added next to the flagged sentence rather than by deleting it. A concern in a
    clause the revision left alone stays on the list, so nothing disappears silently.
    """

    matched_previous = {
        finding.previous_finding_id for finding in created if finding.previous_finding_id is not None
    }
    items: list[ComparisonItem] = []
    for previous in previous_findings:
        if previous.id in matched_previous:
            continue
        clause = clauses_by_index.get(previous.clause_index)
        revised_text = (clause.text if clause else "").strip()
        previous_text = (previous.clause_text or "").strip()
        overlap = similarity(previous_text, revised_text) if previous_text and revised_text else 0.0
        quote_kept = quote_still_present(text, previous.excerpt)
        clause_rewritten = overlap < CLAUSE_UNCHANGED_SIMILARITY

        if not clause_rewritten:
            outcome = OUTCOME_UNRESOLVED
            evidence = (
                f'The clause carrying this concern ("{previous.clause_heading or "untitled"}") is '
                "unchanged in the revised document and this review did not re-raise it, so the "
                "concern is carried forward. Confirm it with a qualified lawyer."
            )
            summary = "The containing clause is unchanged in the revised version."
        else:
            outcome = OUTCOME_FIXED
            kept_note = (
                " The originally flagged sentence is still on the page, so the cure appears to sit "
                "in the surrounding wording; check that it actually answers the concern."
                if quote_kept
                else ""
            )
            evidence = (
                f'The clause carrying this concern ("{previous.clause_heading or "untitled"}") was '
                f"rewritten in the revised document and this review did not re-raise it. The revised "
                f'clause now reads: "{revised_text[:240]}".{kept_note} A qualified lawyer should '
                "confirm the new wording covers the original concern."
            )
            summary = "The containing clause was rewritten and the concern is no longer raised."
        items.append(
            ComparisonItem(
                finding_id=None,
                previous_finding_id=previous.id,
                outcome=outcome,
                category=previous.category,
                severity=previous.severity,
                title=previous.title,
                clause_citation=citation_for(previous),
                excerpt=previous.excerpt,
                status=previous.status,
                evidence=evidence,
                summary=summary,
            )
        )
    return items


def _build_comparison(
    review: DocumentReview,
    previous_review: DocumentReview | None,
    created: list[ReviewFinding],
    resolved: dict[int, str],
    dropped: list[ComparisonItem] | None = None,
) -> ComparisonResponse:
    items: list[ComparisonItem] = []
    newly: list[ComparisonItem] = []
    for finding in created:
        if finding.lifecycle == OUTCOME_NEW:
            newly.append(
                ComparisonItem(
                    finding_id=finding.id,
                    previous_finding_id=None,
                    outcome=OUTCOME_NEW,
                    category=finding.category,
                    severity=finding.severity,
                    title=finding.title,
                    clause_citation=citation_for(finding),
                    excerpt=finding.excerpt,
                    status=finding.status,
                    evidence=finding.excerpt,
                    summary=(
                        "Newly introduced by this version of the document."
                        if previous_review
                        else "Raised by the first review of this document."
                    ),
                )
            )
            continue
        outcome = resolved.get(finding.id) or finding.lifecycle
        items.append(
            ComparisonItem(
                finding_id=finding.id,
                previous_finding_id=finding.previous_finding_id,
                outcome=outcome,
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                clause_citation=citation_for(finding),
                excerpt=finding.excerpt,
                status=finding.status,
                evidence=finding.resolution_evidence,
                summary=(
                    f"Addressed in this version. {finding.resolution_evidence}".strip()
                    if outcome == OUTCOME_FIXED
                    else "Still present in the revised version."
                ),
            )
        )
    fixed = [item for item in items if item.outcome == OUTCOME_FIXED]
    unresolved = [
        item for item in items if item.outcome in {OUTCOME_UNRESOLVED, OUTCOME_CARRIED_OVER}
    ]
    all_items = items + newly + list(dropped or [])
    fixed.extend(item for item in (dropped or []) if item.outcome == OUTCOME_FIXED)
    unresolved.extend(
        item for item in (dropped or []) if item.outcome in {OUTCOME_UNRESOLVED, OUTCOME_CARRIED_OVER}
    )
    return ComparisonResponse(
        review_id=review.id,
        previous_review_id=previous_review.id if previous_review else None,
        previous_filename=previous_review.filename if previous_review else "",
        items=all_items,
        fixed=fixed,
        unresolved=unresolved,
        newly_introduced=newly,
        fixed_count=len(fixed),
        unresolved_count=len(unresolved),
        new_count=len(newly),
        disclaimer=AUTOMATED_ANALYSIS_DISCLAIMER,
    )


def apply_comparison(
    db: Session,
    review: DocumentReview,
    provider: Any,
    previous_review: DocumentReview | None,
    previous_findings: list[ReviewFinding],
    created: list[ReviewFinding],
    clauses: list[Any],
    text: str,
) -> ComparisonResponse:
    clauses_by_index = {clause.index: clause for clause in clauses}
    if previous_review is None:
        for finding in created:
            finding.lifecycle = OUTCOME_NEW
        response = _build_comparison(review, None, created, {})
        review.fixed_count = response.fixed_count
        review.unresolved_count = response.unresolved_count
        review.new_count = response.new_count
        return response

    raw_items: list[dict[str, Any]] = []
    if previous_findings:
        try:
            result = provider.compare_versions(
                [
                    {
                        "id": finding.id,
                        "title": finding.title,
                        "category": finding.category,
                        "severity": finding.severity,
                        "clause_heading": finding.clause_heading,
                        "excerpt": finding.excerpt,
                        "explanation": finding.explanation,
                    }
                    for finding in previous_findings
                ],
                previous_review.extracted_text,
                text,
                clause_payloads(clauses),
            )
            _record_usage(db, review.user_id, "review_compare", result.provider, len(text), True)
            raw_items = [
                item for item in _as_list(result.data.get("findings")) if isinstance(item, dict)
            ]
        except AIProviderError:
            raw_items = []

    by_previous = {finding.id: finding for finding in previous_findings}
    if raw_items:
        resolution = _resolution_from_provider(
            raw_items, by_previous, created, text, clauses_by_index
        )
    else:
        resolution = _resolution_from_text(
            previous_findings, created, text, clauses_by_index
        )
    for finding in created:
        if finding.id not in resolution:
            finding.lifecycle = OUTCOME_NEW

    dropped = _dropped_items(previous_findings, created, text, clauses_by_index)
    response = _build_comparison(review, previous_review, created, resolution, dropped)
    review.fixed_count = response.fixed_count
    review.unresolved_count = response.unresolved_count
    review.new_count = response.new_count
    return response


# --------------------------------------------------------------------------- orchestration


def _record_upload_version(
    db: Session, document: Document, extracted: ExtractedDocument, filename: str
) -> DocumentVersion:
    """Store the analysed upload as a document version, reusing unchanged content."""

    digest = content_hash(extracted.text)
    existing = latest_version(db, document.id)
    if existing is not None and existing.content_hash == digest:
        return existing
    version = DocumentVersion(
        document_id=document.id,
        version_number=document.current_version + 1,
        title=document.title[:240],
        content_html=f"<pre>{escape_text(extracted.text)}</pre>",
        content_text=extracted.text,
        change_note=f"Analysed upload: {filename[:180]}"[:240],
        origin="upload",
        source_filename=filename[:255],
        file_type=extracted.file_type,
        pages=list(extracted.pages),
        page_reference_kind=extracted.page_reference_kind,
        page_count=extracted.page_count,
        word_count=extracted.word_count,
        content_hash=digest,
    )
    db.add(version)
    db.flush()
    document.current_version = version.version_number
    return version


def analyze_document(
    db: Session,
    user: User,
    provider: Any,
    document: Document | None,
    extracted: ExtractedDocument,
    filename: str,
    previous_review: DocumentReview | None,
) -> tuple[DocumentReview, list[Any], ComparisonResponse]:
    """Run clause-level analysis for one document version and persist the result."""

    text = extracted.text
    round_number = (document.review_round + 1) if document is not None else 1
    if round_number > settings.max_review_rounds:
        raise ReviewServiceError(
            409,
            "review_round_limit",
            f"This document has reached the {settings.max_review_rounds}-round comparison limit.",
        )
    clause_units = segment_clauses(extracted)[: settings.max_clauses_per_review]
    if not clause_units:
        raise ReviewServiceError(
            422, "no_clauses", "No clause-level text could be located in the uploaded document."
        )

    if previous_review is not None and previous_review.document_id is not None:
        if document is None or document.id != previous_review.document_id:
            raise ReviewServiceError(
                400,
                "review_document_mismatch",
                "The comparison baseline belongs to a different document, so it cannot be used here.",
            )

    review = DocumentReview(
        user_id=user.id,
        document_id=document.id if document is not None else None,
        filename=filename[:255],
        file_type=extracted.file_type,
        extracted_text=text[:STORED_TEXT_LIMIT],
        summary="",
        document_title=((document.title if document is not None else filename) or "")[:240],
        page_count=extracted.page_count,
        word_count=extracted.word_count,
        clause_count=len(clause_units),
        pages=list(extracted.pages),
        page_reference_kind=extracted.page_reference_kind,
        status="processing",
        round_number=round_number,
        parent_review_id=previous_review.id if previous_review is not None else None,
        version_number=(document.current_version + 1) if document is not None else 1,
        provider=str(getattr(provider, "name", "unknown"))[:32],
        model=str(getattr(provider, "model", ""))[:120],
        disclaimer=AUTOMATED_ANALYSIS_DISCLAIMER,
    )
    db.add(review)
    db.flush()

    if document is not None:
        version = _record_upload_version(db, document, extracted, filename)
        review.document_version_id = version.id
        review.version_number = version.version_number
        review.document_title = document.title[:240]

    try:
        result = provider.analyze_clauses(
            clause_payloads(clause_units),
            filename,
            document.title if document is not None else "",
        )
    except AIProviderError as exc:
        review.status = "failed"
        _record_usage(
            db,
            user,
            "review_analyze",
            str(getattr(provider, "name", "unknown")),
            len(text),
            False,
            getattr(exc, "code", "ai_error"),
        )
        db.commit()
        raise
    _record_usage(db, user, "review_analyze", result.provider, len(text), True)
    review.provider = result.provider[:32]
    review.model = str(result.model)[:120]

    items = [item for item in _as_list(result.data.get("findings")) if isinstance(item, dict)]
    if items:
        review.summary = _clip(result.data.get("summary"), SUMMARY_LIMIT)
    else:
        items = _fallback_items(db, user, review, provider, text)

    created = _persist_findings(db, user, review, items, clause_units, text)
    db.flush()
    if not created:
        raise ProviderResponseError("The AI provider returned no usable clause findings.")

    previous_findings = review_findings(db, previous_review.id) if previous_review else []
    comparison = apply_comparison(
        db, review, provider, previous_review, previous_findings, created, clause_units, text
    )
    review.status = "completed"
    if not review.summary:
        review.summary = (
            f"{len(created)} clause-level finding(s) across {len(clause_units)} extracted clause(s)."
        )
    if document is not None:
        document.review_round = round_number
    db.commit()
    db.refresh(review)
    return review, clause_units, comparison


# --------------------------------------------------------------------------- read models


def _clause_references(
    clauses: list[Any], findings: list[ReviewFinding]
) -> list[ClauseReference]:
    by_clause: dict[int, list[ReviewFinding]] = {}
    for finding in findings:
        by_clause.setdefault(finding.clause_index, []).append(finding)
    return [
        ClauseReference(
            index=clause.index,
            heading=clause.heading,
            citation=clause.citation,
            page_start=clause.page_start,
            page_end=clause.page_end,
            page_reference_kind=clause.page_reference_kind,
            summary=clause.summary(),
            text=clause.text,
            finding_ids=[finding.id for finding in by_clause.get(clause.index, [])],
            open_finding_count=sum(
                finding.status in {"open", "needs_professional_review"}
                for finding in by_clause.get(clause.index, [])
            ),
        )
        for clause in clauses
    ]


def _stored_clauses(review: DocumentReview) -> list[Any]:
    """Rebuild the analysed clauses for a stored review so reloads stay page-exact."""

    if review.extracted_text:
        pages = list(review.pages or [])
        # Reviews written before pages were stored can still be re-paginated, but only as estimated
        # pages. A source PDF without stored pages must not be given invented page numbers.
        if pages or review.page_reference_kind != "source_page":
            return segment_clauses(
                ExtractedDocument(
                    file_type=review.file_type,
                    text=review.extracted_text,
                    pages=pages,
                    page_reference_kind=review.page_reference_kind,
                )
            )
    version = review.version
    if version is None or not version.pages or not version.content_text:
        return []
    return segment_clauses(
        ExtractedDocument(
            file_type=version.file_type or review.file_type,
            text=version.content_text,
            pages=list(version.pages),
            page_reference_kind=version.page_reference_kind,
        )
    )


def counts_for(findings: list[ReviewFinding]) -> ReviewCounts:
    return ReviewCounts(
        total=len(findings),
        open=sum(finding.status == "open" for finding in findings),
        resolved=sum(finding.status == "resolved" for finding in findings),
        dismissed=sum(finding.status == "dismissed" for finding in findings),
        needs_professional_review=sum(
            finding.status == "needs_professional_review" for finding in findings
        ),
        high=sum(finding.severity == "high" for finding in findings),
        medium=sum(finding.severity == "medium" for finding in findings),
        low=sum(finding.severity == "low" for finding in findings),
    )


def finding_summary(finding: ReviewFinding) -> FindingSummary:
    return FindingSummary(
        id=finding.id,
        review_id=finding.review_id,
        document_id=finding.document_id,
        document_version_id=finding.document_version_id,
        first_review_id=finding.first_review_id,
        previous_finding_id=finding.previous_finding_id,
        clause_index=finding.clause_index,
        clause_heading=finding.clause_heading,
        clause_citation=citation_for(finding),
        page_start=finding.page_start,
        page_end=finding.page_end,
        page_reference_kind=finding.page_reference_kind,
        category=finding.category,
        severity=finding.severity,
        title=finding.title,
        excerpt=finding.excerpt,
        explanation=finding.explanation,
        severity_explanation=finding.severity_explanation,
        suggested_wording=finding.suggested_wording,
        suggested_question=finding.suggested_question,
        status=finding.status,
        status_note=finding.status_note,
        status_evidence=finding.status_evidence,
        status_changed_at=finding.status_changed_at,
        lifecycle=finding.lifecycle,
        resolution_evidence=finding.resolution_evidence,
        round_number=finding.round_number,
        confidence=finding.confidence,
        question_count=len(finding.messages),
        created_at=finding.created_at,
        updated_at=finding.updated_at,
    )


def finding_detail(finding: ReviewFinding) -> FindingDetail:
    return FindingDetail(
        **finding_summary(finding).model_dump(),
        clause_text=finding.clause_text,
        quote_start_offset=finding.quote_start_offset,
        quote_end_offset=finding.quote_end_offset,
    )


def _legacy_findings(findings: list[ReviewFinding]) -> list[ReviewFindingSchema]:
    return [
        ReviewFindingSchema.model_validate(
            {
                "category": finding.category,
                "severity": finding.severity,
                "excerpt": finding.excerpt,
                "explanation": finding.explanation,
                "suggested_question": finding.suggested_question,
            }
        )
        for finding in findings
    ]


def _legacy_findings_from_json(findings: Any) -> list[ReviewFindingSchema]:
    """Read the pre-migration JSON column so an un-backfilled review still lists its findings."""

    items: list[ReviewFindingSchema] = []
    for entry in findings if isinstance(findings, list) else []:
        if not isinstance(entry, dict):
            continue
        candidate = {
            "category": normalize_category(entry.get("category")),
            "severity": normalize_severity(entry.get("severity")),
            "excerpt": str(entry.get("excerpt") or ""),
            "explanation": str(entry.get("explanation") or ""),
            "suggested_question": str(entry.get("suggested_question") or ""),
        }
        if not candidate["excerpt"]:
            continue
        items.append(ReviewFindingSchema.model_validate(candidate))
    return items


def review_response(
    db: Session,
    review: DocumentReview,
    clauses: list[Any] | None = None,
) -> ReviewResponse:
    findings = review_findings(db, review.id)
    resolved_clauses = clauses if clauses is not None else _stored_clauses(review)
    legacy = _legacy_findings(findings) or _legacy_findings_from_json(review.findings)
    return ReviewResponse(
        **review_list_item(review).model_dump(),
        review_id=review.id,
        extracted_text=review.extracted_text,
        findings=legacy,
        detailed_findings=[finding_detail(finding) for finding in findings],
        clauses=_clause_references(resolved_clauses, findings),
        counts=counts_for(findings),
        professional_review_notice=PROFESSIONAL_REVIEW_NOTICE,
        disclaimer=AUTOMATED_ANALYSIS_DISCLAIMER,
    )


def review_list_item(review: DocumentReview) -> ReviewListItem:
    return ReviewListItem(
        id=review.id,
        filename=review.filename,
        file_type=review.file_type,
        document_title=review.document_title,
        document_id=review.document_id,
        document_version_id=review.document_version_id,
        parent_review_id=review.parent_review_id,
        version_number=review.version_number,
        round_number=review.round_number,
        page_count=review.page_count,
        word_count=review.word_count,
        clause_count=review.clause_count,
        page_reference_kind=review.page_reference_kind,
        status=review.status,
        provider=review.provider,
        model=review.model,
        fixed_count=review.fixed_count,
        unresolved_count=review.unresolved_count,
        new_count=review.new_count,
        summary=review.summary,
        created_at=review.created_at,
    )


def list_reviews(
    db: Session, user: User, document_id: int | None = None
) -> tuple[list[ReviewListItem], ReviewCounts]:
    query = select(DocumentReview).where(DocumentReview.user_id == user.id)
    if document_id is not None:
        query = query.where(DocumentReview.document_id == document_id)
    reviews = list(db.scalars(query.order_by(DocumentReview.id.desc()).limit(100)))
    items = [review_list_item(review) for review in reviews]
    review_ids = [review.id for review in reviews]
    if not review_ids:
        return items, ReviewCounts()
    findings = list(
        db.scalars(
            select(ReviewFinding).where(
                ReviewFinding.user_id == user.id, ReviewFinding.review_id.in_(review_ids)
            )
        )
    )
    return items, counts_for(findings)


def comparison_for(
    db: Session, review: DocumentReview, findings: list[ReviewFinding]
) -> ComparisonResponse:
    """Rebuild the comparison for a stored review so a reload matches the analysis.

    Concerns the revision no longer raises are stored as historical items rather than rows on the
    new review, so they have to be recomputed here from the baseline review and the stored clauses.
    Without this a reloaded review would quietly lose every finding the revision cured.
    """

    resolved = {
        finding.id: finding.lifecycle for finding in findings if finding.lifecycle != OUTCOME_NEW
    }
    previous_review = review.parent_review
    if previous_review is None:
        return _build_comparison(review, None, findings, resolved)
    previous_findings = review_findings(db, previous_review.id)
    if not previous_findings:
        return _build_comparison(review, previous_review, findings, resolved)
    clauses_by_index = {clause.index: clause for clause in _stored_clauses(review)}
    dropped = _dropped_items(
        previous_findings, findings, review_text(review), clauses_by_index
    )
    return _build_comparison(review, previous_review, findings, resolved, dropped)


# --------------------------------------------------------------------------- mutations


def update_finding_status(
    db: Session, finding: ReviewFinding, status: str, note: str, evidence: str
) -> ReviewFinding:
    if status not in FINDING_STATUSES:
        raise ReviewServiceError(
            422,
            "invalid_status",
            "Status must be open, resolved, dismissed, or needs professional review.",
        )
    cleaned_note = _clip(note, 4000)
    cleaned_evidence = _clip(evidence, 4000)
    if status == "resolved" and not (cleaned_note or cleaned_evidence):
        raise ReviewServiceError(
            422,
            "evidence_required",
            "Marking a finding resolved requires a note or evidence describing what changed.",
        )
    finding.status = status
    finding.status_note = cleaned_note
    finding.status_evidence = cleaned_evidence
    finding.status_changed_at = datetime.now(timezone.utc)
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def review_text(review: DocumentReview) -> str:
    if review.version is not None and review.version.content_text:
        return review.version.content_text
    return review.extracted_text


def clause_text_for(finding: ReviewFinding) -> str:
    if finding.clause_text:
        return finding.clause_text
    review = finding.review
    return review_text(review)[:4000] if review is not None else ""


def finding_messages(db: Session, finding_id: int) -> list[ReviewMessage]:
    return list(
        db.scalars(
            select(ReviewMessage)
            .where(ReviewMessage.finding_id == finding_id)
            .order_by(ReviewMessage.id)
        )
    )


def message_response(message: ReviewMessage) -> ReviewMessageResponse:
    return ReviewMessageResponse(
        id=message.id,
        finding_id=message.finding_id,
        role=message.role,
        kind=message.kind,
        content=message.content,
        suggested_revision=message.suggested_revision,
        created_at=message.created_at,
    )


def message_history(messages: list[ReviewMessage]) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": message.content[:2000]}
        for message in messages[-HISTORY_TURNS:]
    ]


def register_message(
    db: Session,
    finding: ReviewFinding,
    role: str,
    kind: str,
    content: str,
    suggested_revision: str = "",
    provider: str = "",
    model: str = "",
) -> ReviewMessage:
    message = ReviewMessage(
        finding_id=finding.id,
        user_id=finding.user_id,
        role=role,
        kind=kind,
        content=_clip(content, 20000),
        suggested_revision=_clip(suggested_revision, 8000),
        provider=provider[:32],
        model=str(model)[:120],
    )
    db.add(message)
    db.flush()
    return message


def report_filename(review: DocumentReview) -> str:
    return safe_filename(
        f"{review.document_title or review.filename}-review-report", "legalease-review-report"
    )
