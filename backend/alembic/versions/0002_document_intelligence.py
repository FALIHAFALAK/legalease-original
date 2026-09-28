from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "0002_document_intelligence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

FINDING_CATEGORIES = (
    "unclear_clause",
    "missing_information",
    "inconsistent_detail",
    "ambiguous_wording",
    "unusual_obligation",
    "professional_review",
)
FINDING_SEVERITIES = ("low", "medium", "high")


def upgrade() -> None:
    op.add_column("documents", sa.Column("review_round", sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("documents") as batch:
        batch.alter_column("review_round", server_default=None)

    with op.batch_alter_table("document_versions") as batch:
        batch.add_column(sa.Column("origin", sa.String(length=24), nullable=False, server_default="draft"))
        batch.add_column(sa.Column("source_filename", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("file_type", sa.String(length=30), nullable=True))
        batch.add_column(sa.Column("pages", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column(
                "page_reference_kind", sa.String(length=32), nullable=False, server_default="estimated_page"
            )
        )
        batch.add_column(sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("content_hash", sa.String(length=64), nullable=False, server_default=""))
    op.create_index("ix_document_versions_origin", "document_versions", ["origin"])
    op.create_index("ix_document_versions_content_hash", "document_versions", ["content_hash"])

    with op.batch_alter_table("document_reviews") as batch:
        batch.add_column(
            sa.Column("document_version_id", sa.Integer(), nullable=True)
        )
        batch.add_column(sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("parent_review_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("document_title", sa.String(length=240), nullable=False, server_default=""))
        batch.add_column(sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("clause_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("pages", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column(
                "page_reference_kind", sa.String(length=32), nullable=False, server_default="estimated_page"
            )
        )
        batch.add_column(
            sa.Column("status", sa.String(length=24), nullable=False, server_default="completed")
        )
        batch.add_column(sa.Column("provider", sa.String(length=32), nullable=False, server_default=""))
        batch.add_column(sa.Column("model", sa.String(length=120), nullable=False, server_default=""))
        batch.add_column(sa.Column("fixed_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("unresolved_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("new_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("disclaimer", sa.Text(), nullable=False, server_default=""))
    op.create_index("ix_document_reviews_document_version_id", "document_reviews", ["document_version_id"])
    op.create_index("ix_document_reviews_parent_review_id", "document_reviews", ["parent_review_id"])
    op.create_index("ix_document_reviews_status", "document_reviews", ["status"])
    with op.batch_alter_table("document_reviews") as batch:
        batch.create_foreign_key(
            "fk_document_reviews_document_version_id",
            "document_versions",
            ["document_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_document_reviews_parent_review_id",
            "document_reviews",
            ["parent_review_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "review_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "review_id", sa.Integer(), sa.ForeignKey("document_reviews.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "document_version_id",
            sa.Integer(),
            sa.ForeignKey("document_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "first_review_id", sa.Integer(), sa.ForeignKey("document_reviews.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "previous_finding_id",
            sa.Integer(),
            sa.ForeignKey("review_findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("clause_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clause_heading", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("clause_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("quote_start_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quote_end_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_start", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("page_end", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "page_reference_kind", sa.String(length=32), nullable=False, server_default="estimated_page"
        ),
        sa.Column("category", sa.String(length=40), nullable=False, server_default="unclear_clause"),
        sa.Column("severity", sa.String(length=12), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity_explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("suggested_wording", sa.Text(), nullable=False, server_default=""),
        sa.Column("suggested_question", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("status_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("status_evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("resolution_evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_findings_user_id", "review_findings", ["user_id"])
    op.create_index("ix_review_findings_review_id", "review_findings", ["review_id"])
    op.create_index("ix_review_findings_document_id", "review_findings", ["document_id"])
    op.create_index("ix_review_findings_document_version_id", "review_findings", ["document_version_id"])
    op.create_index("ix_review_findings_category", "review_findings", ["category"])
    op.create_index("ix_review_findings_severity", "review_findings", ["severity"])
    op.create_index("ix_review_findings_status", "review_findings", ["status"])
    op.create_index("ix_review_findings_lifecycle", "review_findings", ["lifecycle"])

    op.create_table(
        "review_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "finding_id", sa.Integer(), sa.ForeignKey("review_findings.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="assistant"),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="explanation"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("suggested_revision", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_messages_finding_id", "review_messages", ["finding_id"])
    op.create_index("ix_review_messages_user_id", "review_messages", ["user_id"])
    op.create_index("ix_review_messages_kind", "review_messages", ["kind"])

    _backfill_legacy_findings()


def _backfill_legacy_findings() -> None:
    """Turn previously stored JSON findings into first-class, trackable rows."""

    connection = op.get_bind()
    reviews = connection.execute(
        sa.text("SELECT id, user_id, filename, findings FROM document_reviews ORDER BY id")
    ).fetchall()
    categories = set(FINDING_CATEGORIES)
    severities = set(FINDING_SEVERITIES)
    for review in reviews:
        raw = review.findings
        if isinstance(raw, (str, bytes)):
            # Raw driver access returns the JSON column as text, not as decoded data.
            try:
                raw = json.loads(raw or "[]")
            except (TypeError, ValueError):
                continue
        if not isinstance(raw, list) or not raw:
            continue
        for position, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                continue
            category = str(item.get("category") or "unclear_clause")
            severity = str(item.get("severity") or "medium")
            excerpt = str(item.get("excerpt") or "")[:1200]
            explanation = str(item.get("explanation") or "")
            if not explanation:
                continue
            heading = "Document-level observation"
            title = excerpt[:120] if excerpt else f"Finding {position}"
            connection.execute(
                sa.text(
                    """
                    INSERT INTO review_findings (
                        user_id, review_id, first_review_id, clause_index, clause_heading,
                        clause_text, excerpt, quote_start_offset, quote_end_offset,
                        page_start, page_end, page_reference_kind, category, severity, title,
                        explanation, suggested_wording, suggested_question, status, lifecycle,
                        round_number, created_at, updated_at
                    ) VALUES (
                        :user_id, :review_id, :review_id, 0, :clause_heading,
                        '', :excerpt, 0, :quote_end,
                        1, 1, 'estimated_page', :category, :severity, :title,
                        :explanation, :suggested_wording, :suggested_question, 'open', 'new', 1,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "user_id": review.user_id,
                    "review_id": review.id,
                    "clause_heading": heading,
                    "excerpt": excerpt,
                    "quote_end": len(excerpt),
                    "category": category if category in categories else "unclear_clause",
                    "severity": severity if severity in severities else "medium",
                    "title": title,
                    "explanation": explanation,
                    "suggested_wording": str(item.get("suggested_wording") or "")[:6000],
                    "suggested_question": str(item.get("suggested_question") or "")[:1000],
                },
            )


def downgrade() -> None:
    op.drop_index("ix_review_messages_kind", table_name="review_messages")
    op.drop_index("ix_review_messages_user_id", table_name="review_messages")
    op.drop_index("ix_review_messages_finding_id", table_name="review_messages")
    op.drop_table("review_messages")
    op.drop_index("ix_review_findings_lifecycle", table_name="review_findings")
    op.drop_index("ix_review_findings_status", table_name="review_findings")
    op.drop_index("ix_review_findings_severity", table_name="review_findings")
    op.drop_index("ix_review_findings_category", table_name="review_findings")
    op.drop_index("ix_review_findings_document_version_id", table_name="review_findings")
    op.drop_index("ix_review_findings_document_id", table_name="review_findings")
    op.drop_index("ix_review_findings_review_id", table_name="review_findings")
    op.drop_index("ix_review_findings_user_id", table_name="review_findings")
    op.drop_table("review_findings")

    with op.batch_alter_table("document_reviews") as batch:
        batch.drop_constraint("fk_document_reviews_parent_review_id", type_="foreignkey")
        batch.drop_constraint("fk_document_reviews_document_version_id", type_="foreignkey")
    op.drop_index("ix_document_reviews_status", table_name="document_reviews")
    op.drop_index("ix_document_reviews_parent_review_id", table_name="document_reviews")
    op.drop_index("ix_document_reviews_document_version_id", table_name="document_reviews")
    with op.batch_alter_table("document_reviews") as batch:
        for column in (
            "disclaimer",
            "new_count",
            "unresolved_count",
            "fixed_count",
            "model",
            "provider",
            "status",
            "page_reference_kind",
            "pages",
            "clause_count",
            "word_count",
            "page_count",
            "document_title",
            "parent_review_id",
            "round_number",
            "version_number",
            "document_version_id",
        ):
            batch.drop_column(column)

    op.drop_index("ix_document_versions_content_hash", table_name="document_versions")
    op.drop_index("ix_document_versions_origin", table_name="document_versions")
    with op.batch_alter_table("document_versions") as batch:
        for column in (
            "content_hash",
            "word_count",
            "page_count",
            "page_reference_kind",
            "pages",
            "file_type",
            "source_filename",
            "origin",
        ):
            batch.drop_column(column)

    with op.batch_alter_table("documents") as batch:
        batch.drop_column("review_round")
