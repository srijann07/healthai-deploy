from datetime import datetime, timezone

from extensions import db


class PhoneOTP(db.Model):
    """Stores one-time passwords for phone-based authentication."""

    __tablename__ = "phone_otps"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    otp_hash = db.Column(db.String(128), nullable=False)
    purpose = db.Column(db.String(30), default="login", nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    @property
    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            now = datetime.utcnow()
        return now > exp

    def __repr__(self) -> str:
        return f"<PhoneOTP {self.phone} purpose={self.purpose} used={self.is_used}>"
