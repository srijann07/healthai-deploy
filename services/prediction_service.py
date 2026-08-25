"""Business logic for AI risk assessments and doctor reviews.

A patient runs an assessment: the engine analyses their reported symptoms
plus the vitals/habits stored on their profile, and the result is snapshotted
into a `Prediction` row with `pending_review` status. The patient's assigned
doctor is notified and can approve or reject the AI output with their own
recommendations.
"""

from datetime import datetime, timezone

from extensions import db
from models.doctor import Doctor
from models.notification import Notification
from models.patient import Patient
from models.prediction import Prediction
from services import health_analysis, validation_service as v
from services.audit_service import log_action
from services.notification_service import notify


class PredictionError(Exception):
    """Raised for prediction flows that must stop the request."""


# Ranges used to sanity-check vitals entered on the assessment form.
_RANGES = {
    "systolic_bp": (60, 260),
    "diastolic_bp": (40, 160),
    "heart_rate": (30, 250),
    "blood_sugar": (20, 800),
    "body_temperature": (32, 44),
    "oxygen_level": (40, 100),
}


def run_assessment(patient: Patient, form_data: dict) -> Prediction:
    """Validate the assessment form, run the engine and persist the result."""
    symptoms = [
        s
        for s in (form_data.getlist("symptoms") or [])
        if s in health_analysis.SYMPTOM_CONDITIONS
    ]
    other_symptoms = (form_data.get("other_symptoms") or "").strip()
    if not symptoms and not other_symptoms:
        raise PredictionError(
            "Please select at least one symptom or describe your symptoms in 'Other symptoms'."
        )

    age = v.validate_number(form_data.get("age"), "Age", 1, 120, integer=True)
    gender = v.validate_choice(form_data.get("gender") or "", "Gender", v.GENDERS)

    vitals = {
        key: v.validate_optional_number(
            form_data.get(key) or "", key.replace("_", " "), lo, hi
        )
        for key, (lo, hi) in _RANGES.items()
    }

    history = patient.medical_history
    inputs = {
        "symptoms": symptoms,
        "age": age,
        "gender": gender,
        "height_cm": patient.height_cm,
        "weight_kg": patient.weight_kg,
        "bmi": patient.bmi,
        "chronic_conditions": (history.chronic_conditions or "")
        if history
        else "",
        "previous_diseases": (history.previous_diseases or "")
        if history
        else "",
        "current_medicines": (history.current_medications or "")
        if history
        else "",
        "family_history": (history.family_history or "") if history else "",
        "smoking_status": (history.smoking_status or "") if history else "",
        "alcohol_consumption": (history.alcohol_consumption or "")
        if history
        else "",
        "exercise_frequency": (history.exercise_frequency or "")
        if history
        else "",
    }
    inputs.update(vitals)

    result = health_analysis.analyze(inputs)

    prediction = Prediction(
        patient=patient,
        # Input snapshot
        symptoms_list=symptoms,
        other_symptoms=other_symptoms or None,
        age=age,
        gender=gender,
        height_cm=patient.height_cm,
        weight_kg=patient.weight_kg,
        bmi=patient.bmi,
        systolic_bp=vitals["systolic_bp"],
        diastolic_bp=vitals["diastolic_bp"],
        heart_rate=vitals["heart_rate"],
        blood_sugar=vitals["blood_sugar"],
        body_temperature=vitals["body_temperature"],
        oxygen_level=vitals["oxygen_level"],
        previous_diseases=(history.previous_diseases or "") if history else "",
        smoking_status=(history.smoking_status or "") if history else "",
        alcohol_consumption=(history.alcohol_consumption or "") if history else "",
        exercise_frequency=(history.exercise_frequency or "") if history else "",
        current_medicines=(history.current_medications or "") if history else "",
        # AI output
        risk_level=result["risk_level"],
        possible_disease=result["possible_disease"],
        confidence=result["confidence"],
        suggestions_list=result["health_suggestions"],
        recommended_specialist=result["recommended_specialist"],
        urgency=result["urgency"],
        model_version=result["model_version"],
        # Routing
        status=Prediction.STATUS_PENDING,
        doctor_id=patient.assigned_doctor_id,
    )
    db.session.add(prediction)
    db.session.commit()

    log_action(
        "prediction_created",
        user_id=patient.user_id,
        entity="prediction",
        entity_id=prediction.id,
        details=(
            f"risk={prediction.risk_level} disease={prediction.possible_disease} "
            f"score={result['score']}"
        ),
    )

    if prediction.doctor_id:
        doctor = prediction.reviewing_doctor
        if doctor and doctor.user:
            notify(
                doctor.user_id,
                "New AI assessment awaiting review",
                f"{prediction.possible_disease} · risk "
                f"{prediction.risk_level} ({prediction.confidence:.0f}% confidence).",
                Notification.CATEGORY_PREDICTION,
                link=f"/doctor/predictions/{prediction.id}/review",
            )

    # Automatically generate clinical PDF report & archive to Cloud Storage (Supabase)
    try:
        from services import pdf_service, report_service

        pdf_bytes = pdf_service.generate_assessment_pdf(prediction)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_service.save_report_bytes(
            patient=patient,
            file_bytes=pdf_bytes,
            original_filename=f"HealthAI_Assessment_{prediction.id}_{timestamp_str}.pdf",
            description=f"AI Health Assessment #{prediction.id} · {prediction.possible_disease} ({prediction.risk_level.upper()} Risk)",
        )
    except Exception as exc:
        from flask import current_app

        current_app.logger.warning(
            "Auto-archive assessment PDF to cloud storage skipped: %s", exc
        )

    return prediction


def review_prediction(
    prediction: Prediction,
    doctor: Doctor,
    decision: str,
    notes: str = "",
    tests: str = "",
    medicines: str = "",
    lifestyle: str = "",
) -> Prediction:
    """Approve or reject an AI prediction and attach the doctor's input."""
    if prediction.status != Prediction.STATUS_PENDING:
        raise PredictionError("This prediction has already been reviewed.")

    if decision not in (Prediction.STATUS_APPROVED, Prediction.STATUS_REJECTED):
        raise PredictionError("Invalid review decision.")

    prediction.status = decision
    prediction.reviewing_doctor = doctor
    prediction.doctor_notes = (notes or "").strip() or None
    prediction.recommended_tests = (tests or "").strip() or None
    prediction.recommended_medicines = (medicines or "").strip() or None
    prediction.lifestyle_recommendations = (lifestyle or "").strip() or None
    prediction.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()

    verdict = "approved" if decision == Prediction.STATUS_APPROVED else "rejected"
    doctor_name = doctor.user.full_name if doctor.user else "Your doctor"
    notify(
        prediction.patient.user_id,
        f"Your assessment was {verdict}",
        f"{doctor_name} reviewed your assessment from "
        f"{prediction.created_at.strftime('%d %b %Y')}.",
        Notification.CATEGORY_REVIEW,
        link=f"/patient/predictions/{prediction.id}",
    )
    log_action(
        f"prediction_{verdict}",
        user_id=doctor.user_id,
        entity="prediction",
        entity_id=prediction.id,
        details=f"risk={prediction.risk_level}",
    )
    return prediction