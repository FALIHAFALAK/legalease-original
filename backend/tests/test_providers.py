import os
import threading
import time

import pytest

from app.config import settings
from app.providers.base import (
    ProviderNotConfiguredError,
    ProviderQuotaError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    extract_json,
)
from app.providers.gemini import GeminiProvider
from app.providers.mock import MockAIProvider
from app.templates import get_definition


def test_mock_provider_never_requires_credentials():
    provider = MockAIProvider()
    template = get_definition("mutual-nda")
    result = provider.generate_document(template, {"document_title": "Test NDA"}, "England")
    assert result.provider == "mock"
    assert result.data["title"] == "Test NDA"
    assert "disclosing party" in result.data["missing_information"]


def test_gemini_provider_reports_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", None)
    with pytest.raises(ProviderNotConfiguredError, match="GEMINI_API_KEY"):
        GeminiProvider()


def test_mock_assistant_does_not_return_a_generic_answer():
    with pytest.raises(ProviderNotConfiguredError):
        MockAIProvider().answer_question("Can my landlord keep my deposit?")


def test_gemini_assistant_forwards_question_history_and_context():
    provider = GeminiProvider(api_key="test-key", model="test-model")
    prompts: list[str] = []

    class RecordingModels:
        def generate_content(self, **kwargs):
            prompts.append(kwargs["contents"])
            return type("Response", (), {"text": '{"answer":"A jurisdiction-aware response."}'})()

    provider._client = type("Client", (), {"models": RecordingModels()})()
    result = provider.answer_question(
        "Can my landlord keep a security deposit?",
        "The lease is governed by an unspecified jurisdiction.",
        [{"role": "user", "content": "I need help understanding the lease."}],
    )

    assert result.data["answer"] == "A jurisdiction-aware response."
    assert "Can my landlord keep a security deposit?" in prompts[0]
    assert "I need help understanding the lease." in prompts[0]
    assert "unspecified jurisdiction" in prompts[0]
    assert "ask which jurisdiction applies" in prompts[0]
    assert "Never invent laws" in prompts[0]


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_AI_TESTS") != "1",
    reason="Set RUN_LIVE_AI_TESTS=1 with a configured Gemini provider to run live questions.",
)
def test_live_gemini_distinct_legal_questions():
    if settings.ai_provider != "gemini" or not settings.gemini_api_key:
        pytest.skip("Live Gemini requires AI_PROVIDER=gemini and GEMINI_API_KEY.")
    provider = GeminiProvider()
    questions = (
        "Can my landlord keep a security deposit?",
        "Can my employer fire me without notice?",
        "What should I do about a defective product?",
    )
    answers = [
        provider.answer_question(question).data.get("answer", "").strip()
        for question in questions
    ]
    assert all(answers)
    assert len(set(answers)) == len(questions)


class _FakeModels:
    def __init__(self, failures: list[Exception] | None = None) -> None:
        self.failures = list(failures or [])
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return type("Response", (), {"text": '{"answer":"Recovered answer."}'})()


def _provider_with(models: _FakeModels) -> GeminiProvider:
    provider = GeminiProvider(api_key="test-key", model="test-model")
    provider._client = type("Client", (), {"models": models})()
    return provider


def test_gemini_retries_transient_high_demand(monkeypatch):
    monkeypatch.setattr(settings, "gemini_retry_base_seconds", 0)
    monkeypatch.setattr(settings, "gemini_max_attempts", 3)
    models = _FakeModels([RuntimeError("503 UNAVAILABLE: this model is experiencing high demand")])
    provider = _provider_with(models)

    assert provider._generate("test") == '{"answer":"Recovered answer."}'
    assert models.calls == 2


class _AlwaysFailingModels:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        raise self.error


def test_gemini_reports_temporary_unavailability_after_retries(monkeypatch):
    monkeypatch.setattr(settings, "gemini_retry_base_seconds", 0)
    monkeypatch.setattr(settings, "gemini_max_attempts", 2)
    models = _AlwaysFailingModels(RuntimeError("503 UNAVAILABLE: high demand"))
    provider = _provider_with(models)

    with pytest.raises(ProviderUnavailableError, match="temporarily unavailable"):
        provider._generate("test")
    assert models.calls == 2


def test_gemini_reports_quota_without_retrying(monkeypatch):
    monkeypatch.setattr(settings, "gemini_retry_base_seconds", 0)
    models = _AlwaysFailingModels(
        RuntimeError("Gemini API quota exceeded for this project. Check your billing plan.")
    )
    provider = _provider_with(models)

    with pytest.raises(ProviderQuotaError, match="quota"):
        provider._generate("test")
    assert models.calls == 1


def test_gemini_retries_rate_limit_then_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "gemini_retry_base_seconds", 0)
    models = _FakeModels([RuntimeError("429 Too Many Requests: rate limit exceeded")])
    provider = _provider_with(models)

    assert provider._generate("test") == '{"answer":"Recovered answer."}'
    assert models.calls == 2


def test_extract_json_handles_fenced_response():
    value = extract_json('```json\n{"answer": "ok"}\n```')
    assert value["answer"] == "ok"


def test_gemini_timeout_returns_without_waiting_for_worker(monkeypatch):
    provider = GeminiProvider(api_key="test-key", model="test-model")
    started = threading.Event()
    release = threading.Event()

    class SlowModels:
        def generate_content(self, **kwargs):
            started.set()
            release.wait(1)
            return type("Response", (), {"text": '{"answer": "late"}'})()

    provider._client = type("Client", (), {"models": SlowModels()})()
    monkeypatch.setattr(settings, "gemini_timeout_seconds", 0.01)
    start = time.monotonic()
    try:
        with pytest.raises(ProviderTimeoutError):
            provider._generate("test")
        elapsed = time.monotonic() - start
    finally:
        release.set()
    assert started.wait(1)
    assert elapsed < 0.5
