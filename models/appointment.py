from datetime import datetime, timezone

from extensions import db


class Appointment(db.Model):
    """Scheduled consultation between a patient and a doctor."""

    __tablename__ = "appointments"

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True
    )
    patient = db.relationship("Patient", back_populates="appointments")
    doctor_id = db.Column(
        db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True
    )
    doctor = db.relationship("Doctor", back_populates="appointments")

    scheduled_at = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    notes = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Appointment #{self.id} {self.status}>"
