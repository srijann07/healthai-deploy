from datetime import date, datetime, timezone

from extensions import db


class Patient(db.Model):
    """Patient profile linked one-to-one with a user account."""

    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    user = db.relationship("User", back_populates="patient_profile")

    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))  # male / female / other
    blood_group = db.Column(db.String(5))
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    address = db.Column(db.String(255))
    emergency_contact = db.Column(db.String(20))

    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"))
    assigned_doctor = db.relationship("Doctor", back_populates="patients")

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    predictions = db.relationship(
        "Prediction",
        back_populates="patient",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    medical_reports = db.relationship(
        "MedicalReport",
        back_populates="patient",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    medical_history = db.relationship(
        "MedicalHistory",
        back_populates="patient",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    @property
    def bmi(self) -> float | None:
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            return round(self.weight_kg / ((self.height_cm / 100) ** 2), 1)
        return None

    def __repr__(self) -> str:
        return f"<Patient user_id={self.user_id}>"
