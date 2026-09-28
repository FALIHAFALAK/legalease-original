"""Contract tests for the fields the review workspace UI depends on.

`lib/types.ts` mirrors these payloads by hand, so a silent rename on either side would only show up
as an empty panel in the browser. These tests pin the exact key sets the UI reads.
"""

from __future__ import annotations

from tests.conftest import register
from tests.test_document_intelligence import ORIGINAL, REVISED, analyse, make_document

FINDING_SUMMARY_KEYS = {
    "id",
    "review_id",
    "document_id",
    "document_version_id",
    "first_review_id",
    "previous_finding_id",
    "clause_index",
    "clause_heading",
    "clause_citation",
    "page_start",
    "page_end",
    "page_reference_kind",
    "category",
    "severity",
    "title",
    "excerpt",
    "explanation",
    "severity_explanation",
    "suggested_wording",
    "suggested_question",
    "status",
    "status_note",
    "status_evidence",
    "status_changed_at",
    "lifecycle",
    "resolution_evidence",
    "round_number",
    "confidence",
    "question_count",
    "created_at",
    "updated_at",
}

CLAUSE_KEYS = {
    "index",
    "heading",
    "citation",
    "page_start",
    "page_end",
    "page_reference_kind",
    "summary",
    "text",
    "finding_ids",
    "open_finding_count",
}

COMPARISON_KEYS = {
    "review_id",
    "previous_review_id",
    "previous_filename",
    "items",
    "fixed",
    "unresolved",
    "newly_introduced",
    "fixed_count",
    "unresolved_count",
    "new_count",
    "disclaimer",
}

COMPARISON_ITEM_KEYS = {
    "finding_id",
    "previous_finding_id",
    "outcome",
    "category",
    "severity",
    "title",
    "clause_citation",
    "excerpt",
    "status",
    "evidence",
    "summary",
}

COUNTS_KEYS = {
    "total",
    "open",
    "resolved",
    "dismissed",
    "needs_professional_review",
    "high",
    "medium",
    "low",
}

REVIEW_KEYS = {
    "id",
    "review_id",
    "filename",
    "file_type",
    "document_title",
    "document_id",
    "document_version_id",
    "parent_review_id",
    "version_number",
    "round_number",
    "page_count",
    "word_count",
    "clause_count",
    "page_reference_kind",
    "status",
    "provider",
    "model",
    "fixed_count",
    "unresolved_count",
    "new_count",
    "summary",
    "created_at",
    "extracted_text",
    "findings",
    "detailed_findings",
    "clauses",
    "counts",
    "professional_review_notice",
    "disclaimer",
}


def test_analysis_response_matches_the_workspace_contract(client):
    register(client)
    body = analyse(client, ORIGINAL)
    assert REVIEW_KEYS <= set(body)
    assert COUNTS_KEYS == set(body["counts"])
    assert CLAUSE_KEYS == set(body["clauses"][0])
    for finding in body["detailed_findings"]:
        assert FINDING_SUMMARY_KEYS <= set(finding)
        assert FINDING_SUMMARY_KEYS | {"clause_text", "quote_start_offset", "quote_end_offset"} == set(
            finding
        )


def test_review_detail_carries_the_comparison_the_panel_renders(client):
    register(client)
    first = analyse(client, ORIGINAL)
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    second = client.post(
        "/api/review",
        files={"file": (REVISED.name, REVISED.read_bytes(), "text/plain")},
        data={"previous_review_id": str(first["review_id"])},
        headers={"X-CSRF-Token": csrf},
    )
    assert second.status_code == 200, second.text

    detail = client.get(f"/api/review/{second.json()['review_id']}").json()
    assert REVIEW_KEYS | {"comparison"} == set(detail)
    comparison = detail["comparison"]
    assert comparison is not None
    assert COMPARISON_KEYS == set(comparison)
    for item in comparison["items"]:
        assert COMPARISON_ITEM_KEYS == set(item)
    assert comparison["fixed"], "the workspace renders a fixed group and it must not be empty"
    assert len(comparison["fixed"]) == comparison["fixed_count"]
    assert len(comparison["unresolved"]) == comparison["unresolved_count"]
    assert len(comparison["newly_introduced"]) == comparison["new_count"]


def test_list_response_matches_the_history_contract(client):
    register(client)
    analyse(client, ORIGINAL)
    listing = client.get("/api/review").json()
    assert set(listing) == {"items", "total", "counts"}
    assert COUNTS_KEYS == set(listing["counts"])
    item = listing["items"][0]
    assert {"id", "filename", "clause_count", "round_number", "created_at"} <= set(item)
    assert "review_id" not in item, "the list uses `id`; the detail payload adds `review_id`"


def test_status_update_returns_the_fields_the_card_replaces(client):
    register(client)
    review = analyse(client, ORIGINAL)
    finding_id = review["detailed_findings"][0]["id"]
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    updated = client.patch(
        f"/api/review/findings/{finding_id}",
        json={"status": "resolved", "note": "Renegotiated", "evidence": "Side letter"},
        headers={"X-CSRF-Token": csrf},
    )
    body = updated.json()
    assert FINDING_SUMMARY_KEYS | {"clause_text", "quote_start_offset", "quote_end_offset"} == set(body)
    assert body["status"] == "resolved"
    assert body["status_note"] == "Renegotiated"
    assert body["status_evidence"] == "Side letter"
    assert body["status_changed_at"]


def test_reanalyze_returns_the_nested_shape_the_page_reads(client):
    register(client)
    document_id = make_document(client)
    review = analyse(client, ORIGINAL, document_id=str(document_id))
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    body = client.post(
        f"/api/review/{review['review_id']}/reanalyze", headers={"X-CSRF-Token": csrf}
    ).json()
    assert set(body) == {"review", "comparison"}
    assert REVIEW_KEYS <= set(body["review"])
    assert body["review"]["parent_review_id"] == review["review_id"]
    assert COMPARISON_KEYS == set(body["comparison"])


def test_report_honours_the_include_switches_the_ui_sends(client):
    register(client)
    review = analyse(client, ORIGINAL)
    finding_id = review["detailed_findings"][0]["id"]
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    client.patch(
        f"/api/review/findings/{finding_id}",
        json={"status": "resolved", "note": "Done"},
        headers={"X-CSRF-Token": csrf},
    )
    base = f"/api/review/{review['review_id']}/report"
    for query in ("", "?include_resolved=false", "?include_questions=false", "?include_resolved=true&include_questions=true"):
        response = client.get(f"{base}{query}")
        assert response.status_code == 200, query
        assert response.content.startswith(b"%PDF")
        assert "attachment" in response.headers["content-disposition"]
