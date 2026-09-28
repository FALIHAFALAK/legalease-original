from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Template
from app.schemas import TemplateDetail, TemplateListResponse, TemplateSummary

router = APIRouter(prefix="/api/templates", tags=["templates"])


def template_summary(template: Template) -> TemplateSummary:
    return TemplateSummary.model_validate(template)


@router.get("", response_model=TemplateListResponse)
def list_templates(
    q: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> TemplateListResponse:
    query = (
        select(Template)
        .where(Template.is_active.is_(True))
        .order_by(Template.category, Template.name)
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.where(
            or_(
                Template.name.ilike(term),
                Template.description.ilike(term),
                Template.category.ilike(term),
            )
        )
    if category:
        query = query.where(Template.category == category)
    templates = list(db.scalars(query))
    categories = sorted({item.category for item in templates})
    return TemplateListResponse(
        items=[template_summary(item) for item in templates],
        total=len(templates),
        categories=categories,
    )


@router.get("/{slug}", response_model=TemplateDetail)
def get_template(slug: str, db: Session = Depends(get_db)) -> TemplateDetail:
    template = db.scalar(
        select(Template).where(Template.slug == slug, Template.is_active.is_(True))
    )
    if not template:
        raise HTTPException(
            status_code=404, detail={"code": "template_not_found", "message": "Template not found."}
        )
    return TemplateDetail(
        id=template.id,
        slug=template.slug,
        name=template.name,
        category=template.category,
        description=template.description,
        estimated_time=template.estimated_time,
        is_active=template.is_active,
        fields=template.fields or [],
        sections=template.sections or [],
        disclaimer=template.disclaimer,
    )
