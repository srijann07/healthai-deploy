from datetime import datetime, timezone

from extensions import db


class MedicalHistory(db.Model):
    """Patient-reported medical history and lifestyle, one row per patient."""

    __tablename__ = "medical_histories"

    SMOKING_NEVER = "never"
    SMOKING_FORMER = "former"
    SMOKING_OCCASIONAL = "occasional"
    SMOKING_REGULAR = "regular"

    ALCOHOL_NONE = "none"
    ALCOHOL_OCCASIONAL = "occasional"
    ALCOHOL_REGULAR = "regular"

    EXERCISE_DAILY = "daily"
    EXERCISE_SEVERAL_WEEK = "several_per_week"
    EXERCISE_FEW_WEEK = "few_per_week"
    EXERCISE_RARELY = "rarely"
    EXERCISE_NEVER = "never"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), unique=True, nullable=False
    )
    patient = db.relationship("Patient", back_populates="medical_history")

    allergies = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)
    previous_diseases = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    family_history = db.Column(db.Text)

    smoking_status = db.Column(db.String(20))
    alcohol_consumption = db.Column(db.String(20))
    exercise_frequency = db.Column(db.String(30))

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MedicalHistory patient_id={self.patient_id}>"