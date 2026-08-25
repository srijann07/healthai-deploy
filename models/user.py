from datetime import datetime, timezone

import bcrypt

from extensions import db
from models.role import Role


class User(db.Model):
    """Core account record for every person on the platform."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    phone = db.Column(db.String(20))
    profile_picture = db.Column(db.String(255))

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role", back_populates="users")

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login_at = db.Column(db.DateTime)

    patient_profile = db.relationship(
        "Patient", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    doctor_profile = db.relationship(
        "Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # --- Password handling (bcrypt) ------------------------------------

    def set_password(self, raw_password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
            )
        except (ValueError, AttributeError):
            return False

    # --- Convenience ----------------------------------------------------

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else ""

    def has_role(self, *role_names: str) -> bool:
        return self.role_name in role_names

    @property
    def can_login(self) -> bool:
        return self.is_active and not self.is_suspended

    @property
    def unread_notification_count(self) -> int:
        if not hasattr(self, "_cached_unread_notif_count"):
            try:
                self._cached_unread_notif_count = self.notifications.filter_by(
                    is_read=False
                ).count()
            except Exception:
                self._cached_unread_notif_count = 0
        return self._cached_unread_notif_count

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role_name})>"
