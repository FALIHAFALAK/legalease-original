from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

FINDING_STATUSES = ("open", "resolved", "dismissed", "needs_professional_review")
FINDING_LIFECYCLES = (
    "new",
    "carried_over",
    "fixed",
    "unresolved",
    "newly_introduced",
    "addressed",
)
FINDING_CATEGORIES = (
    "unclear_clause",
    "missing_information",
    "inconsistent_detail",
    "ambiguous_wording",
    "unusual_obligation",
    "professional_review",
)
FINDING_SEVERITIES = ("low", "medium", "high")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(32), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    documents: Mapped[list[Document]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reviews: Mapped[list[DocumentReview]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    findings: Mapped[list[ReviewFinding]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    review_messages: Mapped[list[ReviewMessage]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    estimated_time: Mapped[str] = mapped_column(String(80), default="5–10 minutes")
    fields: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    sections: Mapped[list[str]] = mapped_column(JSON, default=list)
    generation_instructions: Mapped[str] = mapped_column(Text)
    disclaimer: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    documents: Mapped[list[Document]] = relationship(back_populates="template")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content_html: Mapped[str] = mapped_column(Text, default="")
    content_text: Mapped[str] = mapped_column(Text, default="")
    form_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    missing_information: Mapped[list[str]] = mapped_column(JSON, default=list)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list)
    review_notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    review_round: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="documents")
    template: Mapped[Template] = relationship(back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    reviews: Mapped[list[DocumentReview]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240))
    content_html: Mapped[str] = mapped_column(Text)
    content_text: Mapped[str] = mapped_column(Text)
    change_note: Mapped[str] = mapped_column(String(240), default="Saved edit")
    origin: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pages: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    page_reference_kind: Mapped[str] = mapped_column(String(32), default="estimated_page")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    document: Mapped[Document] = relationship(back_populates="versions")
    reviews: Mapped[list[DocumentReview]] = relationship(back_populates="version")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[AIMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class DocumentReview(Base):
    __tablename__ = "document_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(30))
    extracted_text: Mapped[str] = mapped_column(Text)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    document_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    parent_review_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_reviews.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_title: Mapped[str] = mapped_column(String(240), default="")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    clause_count: Mapped[int] = mapped_column(Integer, default=0)
    pages: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    page_reference_kind: Mapped[str] = mapped_column(String(32), default="estimated_page")
    status: Mapped[str] = mapped_column(String(24), default="completed", index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    fixed_count: Mapped[int] = mapped_column(Integer, default=0)
    unresolved_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    disclaimer: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="reviews")
    document: Mapped[Document | None] = relationship(back_populates="reviews")
    version: Mapped[DocumentVersion | None] = relationship(back_populates="reviews")
    parent_review: Mapped[DocumentReview | None] = relationship(
        back_populates="children", remote_side="DocumentReview.id"
    )
    children: Mapped[list[DocumentReview]] = relationship(back_populates="parent_review")
    finding_rows: Mapped[list[ReviewFinding]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewFinding.id",
        foreign_keys="ReviewFinding.review_id",
    )


class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("document_reviews.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    first_review_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_reviews.id", ondelete="SET NULL"), nullable=True
    )
    previous_finding_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_findings.id", ondelete="SET NULL"), nullable=True
    )
    clause_index: Mapped[int] = mapped_column(Integer, default=0)
    clause_heading: Mapped[str] = mapped_column(String(240), default="")
    clause_text: Mapped[str] = mapped_column(Text, default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    quote_start_offset: Mapped[int] = mapped_column(Integer, default=0)
    quote_end_offset: Mapped[int] = mapped_column(Integer, default=0)
    page_start: Mapped[int] = mapped_column(Integer, default=1)
    page_end: Mapped[int] = mapped_column(Integer, default=1)
    page_reference_kind: Mapped[str] = mapped_column(String(32), default="estimated_page")
    category: Mapped[str] = mapped_column(String(40), default="unclear_clause", index=True)
    severity: Mapped[str] = mapped_column(String(12), default="medium", index=True)
    title: Mapped[str] = mapped_column(String(240), default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    severity_explanation: Mapped[str] = mapped_column(Text, default="")
    suggested_wording: Mapped[str] = mapped_column(Text, default="")
    suggested_question: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    status_note: Mapped[str] = mapped_column(Text, default="")
    status_evidence: Mapped[str] = mapped_column(Text, default="")
    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lifecycle: Mapped[str] = mapped_column(String(32), default="new", index=True)
    resolution_evidence: Mapped[str] = mapped_column(Text, default="")
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[User] = relationship(back_populates="findings")
    review: Mapped[DocumentReview] = relationship(
        back_populates="finding_rows", foreign_keys="ReviewFinding.review_id"
    )
    previous_finding: Mapped[ReviewFinding | None] = relationship(remote_side="ReviewFinding.id")
    messages: Mapped[list[ReviewMessage]] = relationship(
        back_populates="finding", cascade="all, delete-orphan", order_by="ReviewMessage.id"
    )


class ReviewMessage(Base):
    __tablename__ = "review_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("review_findings.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(24), default="assistant")
    kind: Mapped[str] = mapped_column(String(32), default="explanation", index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    suggested_revision: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    finding: Mapped[ReviewFinding] = relationship(back_populates="messages")
    user: Mapped[User] = relationship(back_populates="review_messages")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    operation: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    input_characters: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
