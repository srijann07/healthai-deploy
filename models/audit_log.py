from datetime import datetime, timezone

from extensions import db


class AuditLog(db.Model):
    """Immutable record of security-relevant actions on the platform."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    user = db.relationship("User")

    action = db.Column(db.String(60), nullable=False, index=True)
    entity = db.Column(db.String(60))
    entity_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    details = db.Column(db.String(255))

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} user={self.user_id}>"
