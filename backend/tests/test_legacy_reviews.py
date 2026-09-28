"""Coverage for reviews stored before clause-level intelligence existed.

A review written by an earlier release has no ``pages`` value, no normalized finding rows, and
findings only in the legacy JSON column. These tests pin the upgrade behaviour: the clause panel
must still populate, the JSON must be readable, and findings must survive as rows.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import DocumentReview, ReviewFinding, User
from app.services.review_intelligence import (
    _stored_clauses,
    citation_for,
    comparison_for,
    counts_for,
    review_response,
    review_text,
)
from tests.conftest import register
from tests.test_document_intelligence import ORIGINAL

LEGACY_FINDINGS = [
    {
        "category": "unclear_clause",
        "severity": "high",
        "excerpt": "The Supplier shall use reasonable endeavours to meet the deadline.",
        "explanation": "The obligation is not objectively measurable.",
        "suggested_question": "What counts as reasonable endeavours here?",
    },
    {
        "category": "missing_information",
        "severity": "low",
        "excerpt": "The Client shall pay each invoice within 14 days.",
        "explanation": "No late payment interest is stated.",
        "suggested_question": "Is interest charged on late payment?",
    },
]


def first_user() -> User:
    with SessionLocal() as db:
        return db.scalars(select(User).order_by(User.id)).first()


def insert_legacy_review(user: User, filename: str = "legacy-agreement.txt") -> DocumentReview:
    """Insert a review shaped like one written before the intelligence migration."""

    text = ORIGINAL.read_text(encoding="utf-8")
    with SessionLocal() as db:
        review = DocumentReview(
            user_id=user.id,
            document_id=None,
            document_version_id=None,
            filename=filename,
            file_type="txt",
            extracted_text=text,
            pages=None,
            page_count=None,
            word_count=len(text.split()),
            clause_count=None,
            page_reference_kind="estimated_page",
            status="completed",
            provider="legacy",
            model="legacy",
            findings=list(LEGACY_FINDINGS),
            summary="Legacy review stored before clause-level intelligence.",
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review


def test_legacy_review_without_stored_pages_still_rebuilds_its_clauses(client):
    register(client)
    review = insert_legacy_review(first_user())
    with SessionLocal() as db:
        stored = db.get(DocumentReview, review.id)
        clauses = _stored_clauses(stored)
        assert len(clauses) >= 10, "a legacy review must still show its clause panel"
        assert clauses[0].page_start == 1
        assert all(clause.page_reference_kind == "estimated_page" for clause in clauses)
        assert all("(Page" in clause.citation for clause in clauses)


def test_legacy_review_keeps_its_legacy_finding_shape(client):
    register(client)
    review = insert_legacy_review(first_user())
    with SessionLocal() as db:
        payload = review_response(db, db.get(DocumentReview, review.id))
    assert [item.excerpt for item in payload.findings] == [
        item["excerpt"] for item in LEGACY_FINDINGS
    ]
    assert payload.findings[0].category == "unclear_clause"
    assert payload.findings[0].severity == "high"


def test_legacy_review_without_a_baseline_compares_as_all_new(client):
    register(client)
    review = insert_legacy_review(first_user())
    with SessionLocal() as db:
        stored = db.get(DocumentReview, review.id)
        comparison = comparison_for(db, stored, [])
    assert comparison.previous_review_id is None
    assert comparison.fixed == []
    assert comparison.new_count == 0
    assert "not legal advice" in comparison.disclaimer


def test_review_text_falls_back_to_extracted_text(client):
    register(client)
    review = insert_legacy_review(first_user())
    with SessionLocal() as db:
        stored = db.get(DocumentReview, review.id)
        assert review_text(stored) == ORIGINAL.read_text(encoding="utf-8")


def test_counts_and_citations_work_for_rows_with_partial_metadata(client):
    register(client)
    review = insert_legacy_review(first_user())
    rows = [
        ReviewFinding(
            user_id=review.user_id,
            review_id=review.id,
            document_id=None,
            document_version_id=None,
            first_review_id=review.id,
            previous_finding_id=None,
            clause_index=1,
            clause_heading="1. Scope",
            page_start=1,
            page_end=1,
            page_reference_kind="estimated_page",
            category="unclear_clause",
            severity="medium",
            title="Vague obligation",
            excerpt="reasonable endeavours",
            explanation="Not measurable.",
            status="open",
        )
    ]
    counts = counts_for(rows)
    assert counts.total == 1
    assert counts.open == 1
    assert counts.medium == 1
    assert counts.high == 0
    assert "1. Scope" in citation_for(rows[0])


def test_backfill_migration_converts_legacy_json_into_finding_rows():
    """The 0002 migration must move legacy JSON findings into the normalized table."""

    from alembic.config import Config
    from sqlalchemy import create_engine
    from sqlalchemy import text as sql

    from alembic import command

    root = Path(__file__).resolve().parents[1]
    target = (root / "backfill_check.db").resolve()
    if target.exists():
        target.unlink()
    url = f"sqlite:///{target.as_posix()}"
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    engine = create_engine(url)
    try:
        command.upgrade(config, "0001_initial")
        with engine.begin() as connection:
            connection.execute(
                sql(
                    "INSERT INTO users (id, email, hashed_password, full_name, role, is_active, "
                    "created_at, updated_at) VALUES (1, 'legacy@example.com', 'x', 'Legacy', "
                    "'user', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                sql(
                    "INSERT INTO document_reviews (id, user_id, filename, file_type, "
                    "extracted_text, findings, summary, created_at) VALUES ("
                    "1, 1, 'legacy.txt', 'txt', 'AGREEMENT', :findings, 'Legacy summary', "
                    "CURRENT_TIMESTAMP)"
                ),
                {
                    "findings": (
                        '[{"category": "unclear_clause", "severity": "high", '
                        '"excerpt": "Quote A", "explanation": "Because A", '
                        '"suggested_question": "What about A?"}, '
                        '{"category": "bogus", "severity": "catastrophic", "excerpt": "Quote B", '
                        '"explanation": "Because B", "suggested_wording": "Better wording."}, '
                        '{"category": "missing_information", "severity": "low", '
                        '"excerpt": "Quote C", "explanation": ""}, '
                        '"not a dict", {}]'
                    )
                },
            )

        command.upgrade(config, "head")

        with engine.begin() as connection:
            rows = connection.execute(
                sql(
                    "SELECT category, severity, excerpt, explanation, suggested_wording, "
                    "suggested_question, clause_index, clause_heading, status, lifecycle, "
                    "user_id, page_start, page_reference_kind "
                    "FROM review_findings WHERE review_id = 1 ORDER BY id"
                )
            ).fetchall()

        # The unusable entries (no explanation, not a dict, empty) are skipped, and the unknown
        # category and severity fall back rather than being carried through.
        assert [row.excerpt for row in rows] == ["Quote A", "Quote B"]
        assert [row.category for row in rows] == ["unclear_clause", "unclear_clause"]
        assert [row.severity for row in rows] == ["high", "medium"]
        assert [row.explanation for row in rows] == ["Because A", "Because B"]
        assert rows[0].suggested_question == "What about A?"
        assert rows[1].suggested_wording == "Better wording."
        assert all(row.status == "open" and row.lifecycle == "new" for row in rows)
        assert all(row.user_id == 1 for row in rows)
        assert all(row.clause_index == 0 for row in rows)
        assert all(row.clause_heading == "Document-level observation" for row in rows)
        assert all(row.page_start == 1 for row in rows)
        assert all(row.page_reference_kind == "estimated_page" for row in rows)

        command.downgrade(config, "base")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        engine.dispose()
        if target.exists():
            target.unlink()
