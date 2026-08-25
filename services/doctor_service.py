"""Doctor assignment and doctor-related business logic.

New patients are automatically assigned the currently available doctor
with the fewest assigned patients, so the workload spreads evenly.
"""

from sqlalchemy import func

from extensions import db
from models.doctor import Doctor
from models.notification import Notification
from models.patient import Patient
from models.prediction import Prediction
from services.audit_service import log_action
from services.notification_service import notify


def _doctor_display_name(doctor: Doctor) -> str:
    if doctor and doctor.user:
        return f"Dr. {doctor.user.full_name}"
    return "a doctor"


def assign_doctor_to_patient(patient: Patient) -> Doctor | None:
    """Automatically assign the least-loaded available doctor to a patient.

    Returns the assigned doctor, or None when no doctor is available.
    """
    doctors = (
        Doctor.query.filter_by(is_available=True)
        .outerjoin(Patient, Patient.assigned_doctor_id == Doctor.id)
        .group_by(Doctor.id)
        .order_by(func.count(Patient.id).asc(), Doctor.id.asc())
        .all()
    )
    if not doctors:
        return None

    doctor = doctors[0]
    patient.assigned_doctor = doctor
    db.session.commit()

    patient_name = patient.user.full_name if patient.user else f"Patient #{patient.id}"
    notify(
        patient.user_id,
        "Doctor assigned",
        f"{_doctor_display_name(doctor)} is now your assigned doctor. "
        "They will review your AI risk assessments.",
        Notification.CATEGORY_PROFILE,
        link="/patient/doctor",
    )
    notify(
        doctor.user_id,
        "New patient assigned",
        f"{patient_name} has been assigned to you for reviews and follow-ups.",
        Notification.CATEGORY_PROFILE,
        link="/doctor/patients",
    )
    log_action(
        "doctor_assigned",
        user_id=patient.user_id,
        entity="patient",
        entity_id=patient.id,
        details=f"doctor_id={doctor.id}",
    )
    return doctor


def patient_count_for(doctor: Doctor) -> int:
    return Patient.query.filter_by(assigned_doctor_id=doctor.id).count()


def pending_reviews_for(doctor: Doctor):
    """Predictions awaiting review that belong to this doctor's patients."""
    return (
        Prediction.query.filter(
            Prediction.status == Prediction.STATUS_PENDING,
            Prediction.doctor_id == doctor.id,
        )
        .order_by(Prediction.created_at.desc())
    )