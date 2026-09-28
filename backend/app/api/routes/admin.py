from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin, require_csrf
from app.db import get_db
from app.models import Document, Template, UsageRecord, User
from app.schemas import TemplateSummary, UserPublic
from app.services.template_registry import seed_templates

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
def stats(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict[str, object]:
    require_admin(user)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)
    return {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "documents": db.scalar(select(func.count(Document.id))) or 0,
        "templates": db.scalar(select(func.count(Template.id)).where(Template.is_active.is_(True)))
        or 0,
        "ai_requests_30d": db.scalar(
            select(func.count(UsageRecord.id)).where(UsageRecord.created_at >= since)
        )
        or 0,
        "recent_documents": [
            {
                "id": item.id,
                "title_length": len(item.title or ""),
                "status": item.status,
                "created_at": item.created_at.isoformat(),
            }
            for item in db.scalars(select(Document).order_by(desc(Document.created_at)).limit(8))
        ],
    }


@router.get("/users", response_model=list[UserPublic])
def users(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[UserPublic]:
    require_admin(user)
    return [
        UserPublic.model_validate(item)
        for item in db.scalars(select(User).order_by(desc(User.created_at)))
    ]


@router.patch("/users/{user_id}/role")
def set_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> UserPublic:
    require_admin(user)
    if role not in {"user", "admin"}:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_role", "message": "Role must be user or admin."},
        )
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(
            status_code=404, detail={"code": "user_not_found", "message": "User not found."}
        )
    if target.id == user.id and role != "admin":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "self_demotion",
                "message": "Administrators should not remove their own access in this screen.",
            },
        )
    target.role = role
    db.commit()
    db.refresh(target)
    return UserPublic.model_validate(target)


@router.get("/templates", response_model=list[TemplateSummary])
def templates(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[TemplateSummary]:
    require_admin(user)
    return [
        TemplateSummary.model_validate(item)
        for item in db.scalars(select(Template).order_by(Template.category, Template.name))
    ]


@router.post("/templates/seed")
def reseed_templates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, int]:
    require_admin(user)
    return {"created": seed_templates(db)}
