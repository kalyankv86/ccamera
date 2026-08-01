from sqlalchemy.orm import Session

from ccms.models.audit import AuditLog
from ccms.models.user import User


def record_audit(
    db: Session,
    *,
    user: User | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    """Immutable audit trail entry (FR-14). Called explicitly at the end of every
    mutating endpoint rather than via generic middleware, so target_type/target_id/
    detail stay semantically meaningful."""
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail_jsonb=detail,
            ip=ip,
        )
    )
    db.commit()
