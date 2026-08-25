from datetime import datetime, timezone

from extensions import db


class Notification(db.Model):
    """In-app notification shown in the navbar bell menu."""

    __tablename__ = "notifications"

    CATEGORY_PREDICTION = "prediction"
    CATEGORY_REVIEW = "review"
    CATEGORY_REPORT = "report"
    CATEGORY_PROFILE = "profile"
    CATEGORY_SYSTEM = "system"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    user = db.relationship("User", back_populates="notifications")

    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(20), default=CATEGORY_SYSTEM, nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    @property
    def icon(self) -> str:
        """Bootstrap icon class per category."""
        return {
            self.CATEGORY_PREDICTION: "bi-activity",
            self.CATEGORY_REVIEW: "bi-clipboard2-check",
            self.CATEGORY_REPORT: "bi-file-earmark-medical",
            self.CATEGORY_PROFILE: "bi-person-check",
            self.CATEGORY_SYSTEM: "bi-info-circle",
        }.get(self.category, "bi-bell")

    def __repr__(self) -> str:
        return f"<Notification #{self.id} user={self.user_id}>"
