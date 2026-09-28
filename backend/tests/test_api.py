from app.providers.base import AIResult, ProviderTimeoutError
from tests.conftest import register


def test_health_and_templates(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    ai_health = client.post("/api/health/ai")
    assert ai_health.status_code == 200, ai_health.text
    assert ai_health.json()["verified"] is True
    config = client.get("/api/config")
    assert config.status_code == 200
    assert "configure Gemini" in config.json()["message"]
    templates = client.get("/api/templates?q=confidentiality")
    assert templates.status_code == 200
    assert templates.json()["total"] >= 1
    detail = client.get("/api/templates/mutual-nda")
    assert detail.status_code == 200
    assert detail.json()["fields"]


def test_registration_login_and_me(client):
    created = register(client)
    assert created["user"]["email"] == "owner@example.com"
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["full_name"] == "Test User"
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_assistant_returns_provider_answer_and_separate_disclaimer(client, monkeypatch):
    register(client)
    questions: list[str] = []
    histories: list[list[dict[str, str]]] = []

    class RecordingProvider:
        name = "recording"
        model = "test-model"

        def answer_question(self, question, context="", history=None):
            questions.append(question)
            histories.append(history or [])
            return AIResult(
                data={"answer": f"Answer for: {question}"},
                provider=self.name,
                model=self.model,
            )

    monkeypatch.setattr("app.api.routes.assistant.get_ai_provider", lambda: RecordingProvider())
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    first = client.post(
        "/api/assistant/chat",
        json={"message": "Can my landlord keep a security deposit?"},
        headers={"X-CSRF-Token": csrf},
    )
    assert first.status_code == 200, first.text
    assert first.json()["message"] == "Answer for: Can my landlord keep a security deposit?"
    assert "General legal information only" in first.json()["disclaimer"]

    second = client.post(
        "/api/assistant/chat",
        json={
            "message": "What notice may an employer need in New York?",
            "conversation_id": first.json()["conversation_id"],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert second.status_code == 200, second.text
    assert second.json()["message"] == "Answer for: What notice may an employer need in New York?"
    assert questions == [
        "Can my landlord keep a security deposit?",
        "What notice may an employer need in New York?",
    ]
    assert any(item["content"] == "Can my landlord keep a security deposit?" for item in histories[1])
    assert any(item["content"].startswith("Answer for:") for item in histories[1])


def test_assistant_timeout_is_reported_as_gateway_timeout(client, monkeypatch):
    register(client)

    class TimeoutProvider:
        name = "timeout"
        model = "test-model"

        def answer_question(self, question, context="", history=None):
            raise ProviderTimeoutError("The assistant request timed out.")

    monkeypatch.setattr("app.api.routes.assistant.get_ai_provider", lambda: TimeoutProvider())
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/assistant/chat",
        json={"message": "Can my employer terminate me?"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 504, response.text
    assert response.json()["detail"] == {
        "code": "ai_timeout",
        "message": "The assistant request timed out.",
    }


def test_generation_edit_export_and_history(client):
    register(client)
    template = client.get("/api/templates/mutual-nda").json()
    values = {field["name"]: "Example" for field in template["fields"]}
    values.update(
        {
            "document_title": "Mutual NDA — Atlas",
            "disclosing_party": "Atlas Co",
            "receiving_party": "Northstar LLC",
            "effective_date": "2026-09-25",
            "purpose": "Evaluate a software partnership",
            "term": "2 years",
            "governing_law": "New York",
            "email": "legal@example.com",
        }
    )
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    generated = client.post(
        "/api/documents/generate",
        json={"template_slug": "mutual-nda", "jurisdiction": "New York", "fields": values},
        headers={"X-CSRF-Token": csrf},
    )
    assert generated.status_code == 201, generated.text
    document_id = generated.json()["document_id"]
    assert generated.json()["provider"] == "mock"
    detail = client.get(f"/api/documents/{document_id}")
    assert detail.status_code == 200
    updated = client.patch(
        f"/api/documents/{document_id}",
        json={
            "content_html": detail.json()["content_html"] + "<p>Additional review note.</p>",
            "change_note": "Added note",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    assert updated.json()["current_version"] == 2
    versions = client.get(f"/api/documents/{document_id}/versions")
    assert len(versions.json()) == 2
    pdf = client.get(f"/api/documents/{document_id}/export/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    docx = client.get(f"/api/documents/{document_id}/export/docx")
    assert docx.status_code == 200
    assert docx.content[:2] == b"PK"


def test_document_ownership_is_enforced(client):
    register(client, "first@example.com")
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    template = client.get("/api/templates/general-agreement").json()
    values = {field["name"]: "Example" for field in template["fields"]}
    values.update(
        {
            "document_title": "Private draft",
            "party_one": "A",
            "party_two": "B",
            "purpose": "Test",
            "obligations_one": "One",
            "obligations_two": "Two",
            "term": "30 days",
            "termination": "Notice",
            "governing_law": "England",
        }
    )
    document_id = client.post(
        "/api/documents/generate",
        json={"template_slug": "general-agreement", "fields": values},
        headers={"X-CSRF-Token": csrf},
    ).json()["document_id"]
    client.post("/api/auth/logout")
    register(client, "second@example.com")
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert (
        client.patch(
            f"/api/documents/{document_id}",
            json={"title": "Stolen"},
            headers={"X-CSRF-Token": client.get("/api/auth/csrf").json()["csrf_token"]},
        ).status_code
        == 404
    )


def test_review_accepts_txt(client):
    register(client)
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/review",
        files={"file": ("agreement.txt", b"Agreement between the parties. " * 40, "text/plain")},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["file_type"] == "txt"
    assert body["findings"]
    assert "not a legal opinion" in body["professional_review_notice"]


def test_assistant_and_account_deletion_clears_auth_cookies(client):
    register(client)
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    chat = client.post(
        "/api/assistant/chat",
        json={"message": "What should I review?"},
        headers={"X-CSRF-Token": csrf},
    )
    assert chat.status_code == 503, chat.text
    assert chat.json()["detail"]["code"] == "ai_not_configured"
    assert "GEMINI_API_KEY" in chat.json()["detail"]["message"]
    deleted = client.request(
        "DELETE",
        "/api/auth/account",
        json={"password": "StrongPass123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert deleted.status_code == 204
    assert "le_session=" in deleted.headers.get("set-cookie", "")
    assert "le_csrf=" in deleted.headers.get("set-cookie", "")
    assert client.get("/api/auth/me").status_code == 401
