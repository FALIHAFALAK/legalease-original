from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Template
from app.templates import TEMPLATE_DEFINITIONS


def seed_templates(db: Session) -> int:
    created = 0
    for definition in TEMPLATE_DEFINITIONS:
        template = db.scalar(select(Template).where(Template.slug == definition["slug"]))
        if template is None:
            template = Template(slug=definition["slug"])
            db.add(template)
            created += 1
        template.name = definition["name"]
        template.category = definition["category"]
        template.description = definition["description"]
        template.estimated_time = definition["estimated_time"]
        template.fields = definition["fields"]
        template.sections = definition["sections"]
        template.generation_instructions = definition["generation_instructions"]
        template.disclaimer = definition["disclaimer"]
        template.is_active = True
    db.commit()
    return created
