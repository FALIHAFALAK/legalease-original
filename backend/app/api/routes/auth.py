from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import client_key, get_current_user, rate_limiter, require_csrf
from app.config import settings
from app.db import get_db
from app.models import User
from app.schemas import (
    AuthResponse,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdate,
    RegisterRequest,
    UserPublic,
)
from app.security import create_session_token, hash_password, new_csrf_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def set_auth_cookies(response: Response, user_id: int, csrf_token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        create_session_token(user_id),
        max_age=settings.session_max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=settings.session_max_age,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


def public_user(user: User) -> UserPublic:
    return UserPublic.model_validate(user)


@router.get("/csrf")
def csrf(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(settings.csrf_cookie_name) or new_csrf_token()
    response.set_cookie(
        settings.csrf_cookie_name,
        token,
        max_age=settings.session_max_age,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    return {"csrf_token": token}


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> AuthResponse:
    rate_limiter.check(client_key(request, "register"), 5, 3600)
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "email_exists",
                "message": "An account with this email already exists.",
            },
        )
    role = "admin" if email in settings.admin_email_list else "user"
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "email_exists",
                "message": "An account with this email already exists.",
            },
        ) from exc
    db.refresh(user)
    token = new_csrf_token()
    set_auth_cookies(response, user.id, token)
    return AuthResponse(user=public_user(user), csrf_token=token)


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest, request: Request, _: None = Depends(require_csrf)
) -> dict[str, str]:
    rate_limiter.check(client_key(request, "forgot-password"), 5, 3600)
    return {
        "message": "If an account exists for that email, reset instructions will be sent when email delivery is configured."
    }


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
) -> AuthResponse:
    rate_limiter.check(client_key(request, "login"), 10, 900)
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if (
        not user
        or not verify_password(payload.password, user.hashed_password)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_credentials", "message": "Email or password is incorrect."},
        )
    from datetime import datetime, timezone

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    token = new_csrf_token()
    set_auth_cookies(response, user.id, token)
    return AuthResponse(user=public_user(user), csrf_token=token)


@router.get("/me", response_model=UserPublic)
def me(request: Request, response: Response, db: Session = Depends(get_db)) -> UserPublic:
    user = get_current_user(request, db)
    token = request.cookies.get(settings.csrf_cookie_name) or new_csrf_token()
    if not request.cookies.get(settings.csrf_cookie_name):
        response.set_cookie(
            settings.csrf_cookie_name,
            token,
            max_age=settings.session_max_age,
            httponly=False,
            secure=settings.session_cookie_secure,
            samesite=settings.session_cookie_samesite,
            path="/",
        )
    return public_user(user)


@router.post("/logout")
def logout(response: Response, _: None = Depends(require_csrf)) -> dict[str, str]:
    clear_auth_cookies(response)
    return {"message": "Signed out."}


@router.patch("/profile", response_model=UserPublic)
def update_profile(
    payload: ProfileUpdate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> UserPublic:
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(user)
    return public_user(user)


@router.post("/password", response_model=UserPublic)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> UserPublic:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_password", "message": "Current password is incorrect."},
        )
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return public_user(user)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: DeleteAccountRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> Response:
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=400, detail={"code": "invalid_password", "message": "Password is incorrect."}
        )
    db.delete(user)
    db.commit()
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response

