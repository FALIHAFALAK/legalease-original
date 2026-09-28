from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import admin, assistant, auth, documents, review, templates
from app.config import settings
from app.db import SessionLocal, engine
from app.providers.base import AIProviderError
from app.providers.factory import get_ai_provider
from app.schemas import AiConfigResponse, HealthResponse
from app.services.template_registry import seed_templates

logger = logging.getLogger("legalease")


def seed_if_empty() -> None:
    with SessionLocal() as db:
        seed_templates(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env != "test":
        seed_if_empty()
        logger.info("LegalEase started with AI provider mode %s", settings.ai_provider)
    yield


app = FastAPI(
    title="LegalEase API",
    version="0.1.0",
    description="AI-assisted legal document drafting and general information API.",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


@app.exception_handler(AIProviderError)
async def ai_error_handler(request: Request, exc: AIProviderError) -> JSONResponse:
    status_code = 503
    if getattr(exc, "code", "") == "ai_timeout":
        status_code = 504
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": getattr(exc, "code", "ai_unavailable"), "message": str(exc)}},
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    database_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    return HealthResponse(
        status="ok" if database_status == "ok" else "degraded",
        service="legalease-api",
        environment=settings.app_env,
        database=database_status,
        ai_provider=settings.ai_provider,
        ai_configured=settings.ai_provider == "mock" or settings.gemini_configured,
        ai_verified=False,
    )


@app.get("/api/config", response_model=AiConfigResponse)
def configuration() -> AiConfigResponse:
    message = (
        "The deterministic mock provider is for local drafting and review; configure Gemini before using the assistant."
        if settings.ai_provider == "mock"
        else "Use POST /api/health/ai to verify Gemini without exposing credentials."
    )
    return AiConfigResponse(
        provider=settings.ai_provider,
        model=settings.gemini_model if settings.ai_provider == "gemini" else None,
        configured=settings.ai_provider == "mock" or settings.gemini_configured,
        verified=False,
        message=message,
    )


@app.post("/api/health/ai", response_model=AiConfigResponse)
def verify_ai() -> AiConfigResponse:
    try:
        provider = get_ai_provider()
        verified, message = provider.check_connection()
        return AiConfigResponse(
            provider=provider.name,
            model=getattr(provider, "model", None),
            configured=True,
            verified=verified,
            message=message,
        )
    except AIProviderError as exc:
        return AiConfigResponse(
            provider=settings.ai_provider,
            model=settings.gemini_model if settings.ai_provider == "gemini" else None,
            configured=False,
            verified=False,
            message=str(exc),
        )


app.include_router(auth.router)
app.include_router(templates.router)
app.include_router(documents.router)
app.include_router(assistant.router)
app.include_router(review.router)
app.include_router(admin.router)
