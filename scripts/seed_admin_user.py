"""Idempotent: creates the initial Administrator account if none exists yet."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ccms.auth.security import hash_password  # noqa: E402
from ccms.db import SessionLocal  # noqa: E402
from ccms.models.enums import Role  # noqa: E402
from ccms.models.user import User  # noqa: E402

DEFAULT_EMAIL = os.environ.get("CCMS_ADMIN_EMAIL", "admin@ccms.campus")
DEFAULT_PASSWORD = os.environ.get("CCMS_ADMIN_PASSWORD", "ChangeMe123!")


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == Role.ADMIN).first()
        if existing:
            print(f"Admin user already exists: {existing.email}")
            return
        user = User(
            name="System Administrator",
            email=DEFAULT_EMAIL,
            password_hash=hash_password(DEFAULT_PASSWORD),
            role=Role.ADMIN,
            active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created admin user {DEFAULT_EMAIL} / {DEFAULT_PASSWORD} (change this password immediately)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
