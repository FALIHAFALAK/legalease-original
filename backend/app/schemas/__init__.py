from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TemplateField(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=120)
    type: Literal["text", "textarea", "date", "select", "number", "email"] = "text"
    required: bool = False
    placeholder: str = ""
    help: str = ""
    options: list[str] = Field(default_factory=list)


class TemplateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    category: str
    description: str
    estimated_time: str
    is_active: bool = True


class TemplateDetail(TemplateSummary):
    fields: list[TemplateField]
    sections: list[str]
    disclaimer: str = ""


class TemplateListResponse(BaseModel):
    items: list[TemplateSummary]
    total: int
    categories: list[str]


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Literal["user", "admin"]
    created_at: datetime
    last_login_at: datetime | None = None


class AuthResponse(BaseModel):
    user: UserPublic
    csrf_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("Password must include at least one letter and one number.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("Password must include at least one letter and one number.")
        return value


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class GenerateDocumentRequest(BaseModel):
    template_slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    title: str | None = Field(default=None, min_length=2, max_length=240)
    jurisdiction: str | None = Field(default=None, max_length=120)
    fields: dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    title: str
    content: str
    sections: list[str] = Field(default_factory=list)
    jurisdiction: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)


class GeneratedDocumentResponse(BaseModel):
    document: DocumentMetadata
    document_id: int | None = None
    provider: str
    model: str
    is_draft: bool = True


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: str
    jurisdiction: str | None
    template_slug: str | None = None
    updated_at: datetime
    created_at: datetime
    current_version: int


class DocumentDetail(DocumentSummary):
    content_html: str
    content_text: str
    form_data: dict[str, Any]
    missing_information: list[str]
    assumptions: list[str]
    review_notes: list[str]


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    draft_count: int
    completed_count: int


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    content_html: str | None = Field(default=None, max_length=200000)
    content_text: str | None = Field(default=None, max_length=200000)
    status: Literal["draft", "ready_for_review", "archived"] | None = None
    change_note: str | None = Field(default=None, max_length=240)


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_number: int
    title: str
    content_html: str
    change_note: str
    created_at: datetime


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=6000)
    conversation_id: int | None = None
    document_id: int | None = None


class AssistantResponse(BaseModel):
    conversation_id: int
    message: str
    disclaimer: str
    provider: str
    model: str
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse]


class ReviewFinding(BaseModel):
    category: Literal[
        "unclear_clause",
        "missing_information",
        "inconsistent_detail",
        "ambiguous_wording",
        "unusual_obligation",
        "professional_review",
    ]
    severity: Literal["low", "medium", "high"] = "medium"
    excerpt: str = ""
    explanation: str
    suggested_question: str = ""


class ClauseReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    heading: str
    citation: str
    page_start: int
    page_end: int
    page_reference_kind: str
    summary: str
    text: str
    finding_ids: list[int] = Field(default_factory=list)
    open_finding_count: int = 0


class FindingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    document_id: int | None = None
    document_version_id: int | None = None
    first_review_id: int | None = None
    previous_finding_id: int | None = None
    clause_index: int = 0
    clause_heading: str = ""
    clause_citation: str = ""
    page_start: int = 1
    page_end: int = 1
    page_reference_kind: str = "estimated_page"
    category: str = "unclear_clause"
    severity: str = "medium"
    title: str = ""
    excerpt: str = ""
    explanation: str = ""
    severity_explanation: str = ""
    suggested_wording: str = ""
    suggested_question: str = ""
    status: str = "open"
    status_note: str = ""
    status_evidence: str = ""
    status_changed_at: datetime | None = None
    lifecycle: str = "new"
    resolution_evidence: str = ""
    round_number: int = 1
    confidence: float | None = None
    question_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FindingDetail(FindingSummary):
    clause_text: str = ""
    quote_start_offset: int = 0
    quote_end_offset: int = 0


class FindingStatusUpdate(BaseModel):
    status: Literal["open", "resolved", "dismissed", "needs_professional_review"]
    note: str = Field(default="", max_length=4000)
    evidence: str = Field(default="", max_length=4000)


class ReviewCounts(BaseModel):
    total: int = 0
    open: int = 0
    resolved: int = 0
    dismissed: int = 0
    needs_professional_review: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class ReviewListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    document_title: str = ""
    document_id: int | None = None
    document_version_id: int | None = None
    parent_review_id: int | None = None
    version_number: int = 1
    round_number: int = 1
    page_count: int = 0
    word_count: int = 0
    clause_count: int = 0
    page_reference_kind: str = "estimated_page"
    status: str = "completed"
    provider: str = ""
    model: str = ""
    fixed_count: int = 0
    unresolved_count: int = 0
    new_count: int = 0
    summary: str = ""
    created_at: datetime


class ReviewListResponse(BaseModel):
    items: list[ReviewListItem]
    total: int
    counts: ReviewCounts


class ComparisonItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # None when a previous concern is no longer raised, so there is no current row to point at.
    finding_id: int | None = None
    previous_finding_id: int | None = None
    outcome: str
    category: str = "unclear_clause"
    severity: str = "medium"
    title: str = ""
    clause_citation: str = ""
    excerpt: str = ""
    status: str = "open"
    evidence: str = ""
    summary: str = ""


class ComparisonResponse(BaseModel):
    review_id: int
    previous_review_id: int | None = None
    previous_filename: str = ""
    items: list[ComparisonItem] = Field(default_factory=list)
    fixed: list[ComparisonItem] = Field(default_factory=list)
    unresolved: list[ComparisonItem] = Field(default_factory=list)
    newly_introduced: list[ComparisonItem] = Field(default_factory=list)
    fixed_count: int = 0
    unresolved_count: int = 0
    new_count: int = 0
    disclaimer: str = ""


class ReviewResponse(ReviewListItem):
    """Clause-level review payload. The legacy finding shape is preserved for existing clients."""

    review_id: int = 0
    extracted_text: str = ""
    findings: list[ReviewFinding] = Field(default_factory=list)
    detailed_findings: list[FindingDetail] = Field(default_factory=list)
    clauses: list[ClauseReference] = Field(default_factory=list)
    counts: ReviewCounts = Field(default_factory=ReviewCounts)
    professional_review_notice: str = ""
    disclaimer: str = ""


class ReviewDetailResponse(ReviewResponse):
    comparison: ComparisonResponse | None = None


class FindingQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    request_revision: bool = False


class ReviewMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: int
    role: str
    kind: str
    content: str
    suggested_revision: str = ""
    created_at: datetime


class FindingQuestionResponse(BaseModel):
    finding_id: int
    question_id: int | None = None
    answer_id: int | None = None
    question: str
    answer: str
    suggested_revision: str = ""
    suggested_wording: str = ""
    disclaimer: str
    provider: str
    model: str
    messages: list[ReviewMessageResponse] = Field(default_factory=list)
    created_at: datetime | None = None


class ReanalyzeResponse(BaseModel):
    review: ReviewResponse
    comparison: ComparisonResponse | None = None


class ReviewErrorResponse(BaseModel):
    code: str
    message: str



class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    database: str
    ai_provider: str
    ai_configured: bool
    ai_verified: bool = False


class AiConfigResponse(BaseModel):
    provider: str
    model: str | None
    configured: bool
    verified: bool = False
    message: str
