from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AI_PROVIDER", "mock")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-legalease")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_legalease.db")

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import rate_limiter
from app.db import Base, SessionLocal, engine
from app.main import app
from app.services.template_registry import seed_templates


@pytest.fixture()
def client():
    rate_limiter.reset()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_templates(db)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def register(client: TestClient, email: str = "owner@example.com") -> dict:
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    response = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test User", "password": "StrongPass123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201, response.text
    return response.json()
