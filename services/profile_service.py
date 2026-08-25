"""Business logic for patient profile management and password changes."""

from extensions import db
from models.medical_history import MedicalHistory
from models.notification import Notification
from models.patient import Patient
from models.user import User
from services import validation_service as v
from services.audit_service import log_action
from services.notification_service import notify


class ProfileError(Exception):
    """Raised for profile operations that require the caller to stop."""


def update_personal_details(user: User, data: dict) -> User:
    """Update the account contact details (names + phone). Email is immutable."""
    first_name = v.validate_name(data.get("first_name"), "First name")
    last_name = v.validate_name(data.get("last_name"), "Last name")
    phone = v.validate_phone(data.get("phone", ""))

    user.first_name = first_name
    user.last_name = last_name
    user.phone = phone or None
    db.session.commit()
    log_action("profile_updated", user_id=user.id, entity="user", entity_id=user.id)
    return user


def update_health_information(patient: Patient, data: dict) -> Patient:
    """Update demographics and vitals fields on the patient profile."""
    dob = v.validate_date(data.get("date_of_birth"), "Date of birth")
    gender_raw = (data.get("gender") or "").strip()
    gender = (
        v.validate_choice(gender_raw, "Gender", v.GENDERS) if gender_raw else None
    )
    blood_raw = (data.get("blood_group") or "").strip()
    blood_group = (
        v.validate_choice(blood_raw, "Blood group", v.BLOOD_GROUPS)
        if blood_raw
        else None
    )
    height_cm = v.validate_optional_number(data.get("height_cm"), "Height", 30, 250)
    weight_kg = v.validate_optional_number(data.get("weight_kg"), "Weight", 5, 300)
    address = v.validate_optional_text(
        data.get("address") or "", "Address", max_length=255
    ) or None
    emergency_contact = (
        v.validate_phone(data.get("emergency_contact", "")) or None
    )

    patient.date_of_birth = dob
    patient.gender = gender
    patient.blood_group = blood_group
    patient.height_cm = height_cm
    patient.weight_kg = weight_kg
    patient.address = address
    patient.emergency_contact = emergency_contact
    db.session.commit()
    log_action(
        "health_information_updated", user_id=patient.user_id, entity="patient",
        entity_id=patient.id,
    )
    return patient


def update_medical_history(patient: Patient, data: dict) -> MedicalHistory:
    allergies = (
        v.validate_optional_text(data.get("allergies") or "", "Allergies") or None
    )
    chronic_conditions = (
        v.validate_optional_text(
            data.get("chronic_conditions") or "", "Chronic conditions"
        )
        or None
    )
    previous_diseases = (
        v.validate_optional_text(
            data.get("previous_diseases") or "", "Previous diseases"
        )
        or None
    )
    current_medications = (
        v.validate_optional_text(
            data.get("current_medications") or "", "Current medications"
        )
        or None
    )
    family_history = (
        v.validate_optional_text(data.get("family_history") or "", "Family history")
        or None
    )

    smoking = (data.get("smoking_status") or "").strip()
    smoking_status = (
        v.validate_choice(smoking, "Smoking status", v.SMOKING_STATUSES)
        if smoking
        else None
    )
    alcohol = (data.get("alcohol_consumption") or "").strip()
    alcohol_consumption = (
        v.validate_choice(alcohol, "Alcohol consumption", v.ALCOHOL_LEVELS)
        if alcohol
        else None
    )
    exercise = (data.get("exercise_frequency") or "").strip()
    exercise_frequency = (
        v.validate_choice(exercise, "Exercise frequency", v.EXERCISE_LEVELS)
        if exercise
        else None
    )

    history = patient.medical_history or MedicalHistory(patient=patient)
    history.allergies = allergies
    history.chronic_conditions = chronic_conditions
    history.previous_diseases = previous_diseases
    history.current_medications = current_medications
    history.family_history = family_history
    history.smoking_status = smoking_status
    history.alcohol_consumption = alcohol_consumption
    history.exercise_frequency = exercise_frequency

    if history not in db.session:
        db.session.add(history)
    db.session.commit()
    log_action(
        "medical_history_updated", user_id=patient.user_id, entity="patient",
        entity_id=patient.id,
    )
    return history


def change_password(user: User, current: str, new: str, confirm: str) -> User:
    """Change the password after verifying the current one."""
    if not user.check_password(current or ""):
        log_action("password_change_failed", user_id=user.id)
        raise ProfileError("Your current password is incorrect.")

    v.validate_password_strength(new)
    if new != confirm:
        raise v.ValidationError("New passwords do not match.")

    user.set_password(new)
    db.session.commit()
    log_action("password_changed", user_id=user.id)
    notify(
        user.id,
        "Password changed",
        "Your account password was changed. If this wasn't you, contact support "
        "immediately.",
        Notification.CATEGORY_PROFILE,
    )
    return user