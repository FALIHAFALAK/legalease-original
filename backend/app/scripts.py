from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password
from app.services.template_registry import seed_templates


def main() -> None:
    parser = argparse.ArgumentParser(description="LegalEase administrative utility")
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed_parser = subparsers.add_parser("seed-templates")
    seed_parser.set_defaults(func=seed)
    admin_parser = subparsers.add_parser("create-admin")
    admin_parser.add_argument("--email", required=True)
    admin_parser.add_argument("--name", required=True)
    admin_parser.add_argument("--password", required=True)
    admin_parser.set_defaults(func=create_admin)
    args = parser.parse_args()
    args.func(args)


def seed(_: argparse.Namespace) -> None:
    with SessionLocal() as db:
        created = seed_templates(db)
    print(f"Seeded templates. New rows: {created}")


def create_admin(args: argparse.Namespace) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email.lower().strip()))
        if user:
            user.role = "admin"
            user.is_active = True
            db.commit()
            print("Promoted existing user to admin.")
            return
        user = User(
            email=args.email.lower().strip(),
            full_name=args.name,
            hashed_password=hash_password(args.password),
            role="admin",
        )
        db.add(user)
        db.commit()
        print("Created admin user.")


if __name__ == "__main__":
    main()
