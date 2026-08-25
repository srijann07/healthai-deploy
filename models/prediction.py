import json
from datetime import datetime, timezone

from extensions import db


class Prediction(db.Model):
    """One AI health-risk prediction, plus the doctor's review of it."""

    __tablename__ = "predictions"

    STATUS_PENDING = "pending_review"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    RISK_LEVELS = ("Low", "Medium", "High", "Critical")

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True
    )
    patient = db.relationship("Patient", back_populates="predictions")

    # --- Input snapshot (vitals as entered at prediction time) ----------
    symptoms = db.Column(db.Text, nullable=False, default="[]")  # JSON list
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    bmi = db.Column(db.Float)
    systolic_bp = db.Column(db.Integer)
    diastolic_bp = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    blood_sugar = db.Column(db.Float)
    body_temperature = db.Column(db.Float)
    oxygen_level = db.Column(db.Float)
    previous_diseases = db.Column(db.String(255))
    smoking_status = db.Column(db.String(20))
    alcohol_consumption = db.Column(db.String(20))
    exercise_frequency = db.Column(db.String(20))
    current_medicines = db.Column(db.String(255))

    # --- AI output ------------------------------------------------------
    risk_level = db.Column(db.String(20), nullable=False, index=True)
    possible_disease = db.Column(db.String(120), index=True)
    confidence = db.Column(db.Float)  # 0-100
    health_suggestions = db.Column(db.Text)  # JSON list of strings
    recommended_specialist = db.Column(db.String(100))
    urgency = db.Column(db.String(50))
    model_version = db.Column(db.String(50))

    # --- Doctor review --------------------------------------------------
    status = db.Column(
        db.String(20), default=STATUS_PENDING, nullable=False, index=True
    )
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"))
    reviewing_doctor = db.relationship("Doctor", back_populates="reviewed_predictions")
    doctor_notes = db.Column(db.Text)
    recommended_tests = db.Column(db.Text)
    recommended_medicines = db.Column(db.Text)
    lifestyle_recommendations = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # --- JSON helpers ---------------------------------------------------

    @property
    def symptoms_list(self) -> list[str]:
        try:
            return json.loads(self.symptoms or "[]")
        except (TypeError, ValueError):
            return []

    @symptoms_list.setter
    def symptoms_list(self, value: list[str]) -> None:
        self.symptoms = json.dumps(value or [])

    @property
    def suggestions_list(self) -> list[str]:
        try:
            return json.loads(self.health_suggestions or "[]")
        except (TypeError, ValueError):
            return []

    @suggestions_list.setter
    def suggestions_list(self, value: list[str]) -> None:
        self.health_suggestions = json.dumps(value or [])

    @property
    def risk_badge(self) -> str:
        """Bootstrap contextual class for the risk level."""
        return {
            "Low": "success",
            "Medium": "warning",
            "High": "danger",
            "Critical": "dark",
        }.get(self.risk_level, "secondary")

    def __repr__(self) -> str:
        return f"<Prediction #{self.id} {self.risk_level} patient={self.patient_id}>"
