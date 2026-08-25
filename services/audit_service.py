"""Audit trail writer. Call `log_action` after any security-relevant event."""

from flask import request

from extensions import db
from models.audit_log import AuditLog


def log_action(
    action: str,
    user_id: int | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    details: str | None = None,
) -> None:
    """Persist an audit log entry. Never raises — auditing must not break flows."""
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr) if request else None
        db.session.add(
            AuditLog(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                ip_address=(ip or "")[:45] or None,
                details=(details or "")[:255] or None,
            )
        )
        db.session.commit()
    except Exception:  # pragma: no cover - defensive
        db.session.rollback()
