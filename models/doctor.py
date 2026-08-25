from datetime import datetime, timezone

from extensions import db


class Doctor(db.Model):
    """Doctor profile linked one-to-one with a user account."""

    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    user = db.relationship("User", back_populates="doctor_profile")

    specialization = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(60), unique=True)
    years_experience = db.Column(db.Integer, default=0)
    hospital = db.Column(db.String(150))
    bio = db.Column(db.Text)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    patients = db.relationship(
        "Patient", back_populates="assigned_doctor", lazy="dynamic"
    )
    reviewed_predictions = db.relationship(
        "Prediction", back_populates="reviewing_doctor", lazy="dynamic"
    )
    appointments = db.relationship(
        "Appointment", back_populates="doctor", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Doctor user_id={self.user_id} {self.specialization}>"
