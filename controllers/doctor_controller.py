"""Request handling for the doctor module.

Doctors see their assigned patients, review AI assessments (approve or
reject with their own recommendations) and manage appointment requests.
"""

from flask import abort, current_app, flash, redirect, render_template, request, url_for

from extensions import db
from middlewares.auth_middleware import get_current_user, role_required
from models.appointment import Appointment
from models.patient import Patient
from models.prediction import Prediction
from models.role import Role
from models.user import User
from services import appointment_service, doctor_service
from services.appointment_service import AppointmentError
from services.audit_service import log_action
from services.prediction_service import PredictionError, review_prediction


def _doctor():
    user = get_current_user()
    if user is None or user.doctor_profile is None:
        abort(403)
    return user.doctor_profile


@role_required(Role.DOCTOR)
def patients_page():
    """List the doctor's assigned patients with search + risk filter."""
    doctor = _doctor()
    query = (
        Patient.query.join(User, User.id == Patient.user_id)
        .filter(Patient.assigned_doctor_id == doctor.id)
        .order_by(User.first_name.asc(), User.last_name.asc())
    )

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
            )
        )

    risk = request.args.get("risk", "")
    if risk in Prediction.RISK_LEVELS:
        patient_ids = [
            row[0]
            for row in db.session.query(Prediction.patient_id)
            .filter(Prediction.risk_level == risk)
            .distinct()
            .all()
        ]
        query = query.filter(Patient.id.in_(patient_ids))

    pagination = query.paginate(
        page=request.args.get("page", 1, type=int),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    latest_by_patient = {}
    if pagination.items:
        patient_ids = [p.id for p in pagination.items]
        rows = (
            db.session.query(Prediction)
            .filter(Prediction.patient_id.in_(patient_ids))
            .order_by(Prediction.patient_id, Prediction.created_at.desc())
            .all()
        )
        seen = set()
        for row in rows:
            if row.patient_id not in seen:
                latest_by_patient[row.patient_id] = row
                seen.add(row.patient_id)
    return render_template(
        "doctor/patients.html",
        pagination=pagination,
        search=search,
        risk=risk,
        risk_levels=Prediction.RISK_LEVELS,
        latest_by_patient=latest_by_patient,
    )


@role_required(Role.DOCTOR)
def patient_detail_page(patient_id: int):
    """Full view of one assigned patient: profile, history, assessments."""
    doctor = _doctor()
    patient = db.session.get(Patient, patient_id)
    if patient is None or patient.assigned_doctor_id != doctor.id:
        abort(404)
    predictions = (
        patient.predictions.order_by(Prediction.created_at.desc()).all()
    )
    return render_template(
        "doctor/patient_detail.html",
        patient=patient,
        predictions=predictions,
        pending_count=doctor_service.pending_reviews_for(doctor).count(),
    )


@role_required(Role.DOCTOR)
def predictions_page():
    """Review queue: assessments pending review from the doctor's patients."""
    doctor = _doctor()
    tab = request.args.get("tab", "pending")
    if tab == "reviewed":
        query = Prediction.query.filter(
            Prediction.doctor_id == doctor.id,
            Prediction.status.in_(
                [Prediction.STATUS_APPROVED, Prediction.STATUS_REJECTED]
            ),
        )
    else:
        query = doctor_service.pending_reviews_for(doctor)
        tab = "pending"

    pagination = (
        query.order_by(Prediction.created_at.desc())
        .paginate(
            page=request.args.get("page", 1, type=int),
            per_page=current_app.config["ITEMS_PER_PAGE"],
            error_out=False,
        )
    )
    return render_template(
        "doctor/predictions.html",
        pagination=pagination,
        tab=tab,
        pending_count=doctor_service.pending_reviews_for(doctor).count(),
    )


@role_required(Role.DOCTOR)
def review_prediction_page(prediction_id: int):
    """Approve or reject one AI assessment with the doctor's input."""
    doctor = _doctor()
    prediction = db.session.get(Prediction, prediction_id)
    if prediction is None or prediction.doctor_id != doctor.id:
        abort(404)

    if request.method == "POST":
        try:
            review_prediction(
                prediction,
                doctor,
                request.form.get("decision", ""),
                notes=request.form.get("notes", ""),
                tests=request.form.get("tests", ""),
                medicines=request.form.get("medicines", ""),
                lifestyle=request.form.get("lifestyle", ""),
            )
        except PredictionError as exc:
            flash(str(exc), "danger")
            return render_template(
                "doctor/prediction_review.html",
                prediction=prediction,
                values=request.form.to_dict(),
            ), 400
        flash(
            "Assessment "
            f"{prediction.status}. The patient has been notified.",
            "success",
        )
        return redirect(url_for("doctor.predictions_page"))

    return render_template(
        "doctor/prediction_review.html",
        prediction=prediction,
        values={},
    )


@role_required(Role.DOCTOR)
def appointments_page():
    """Appointments for this doctor, with confirm/complete/cancel actions."""
    doctor = _doctor()
    user = get_current_user()

    if request.method == "POST":
        appointment = db.session.get(
            Appointment, request.form.get("appointment_id", type=int)
        )
        action = request.form.get("action", "")
        status_map = {
            "confirm": Appointment.STATUS_CONFIRMED,
            "complete": Appointment.STATUS_COMPLETED,
            "cancel": Appointment.STATUS_CANCELLED,
        }
        if appointment is None or appointment.doctor_id != doctor.id:
            abort(404)
        try:
            appointment_service.set_appointment_status(
                appointment, status_map.get(action, ""), user
            )
        except AppointmentError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Appointment {action}ed.", "success")
        return redirect(url_for("doctor.appointments_page"))

    upcoming = (
        doctor.appointments.filter(
            Appointment.status.in_(
                [Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]
            )
        )
        .order_by(Appointment.scheduled_at.asc())
        .all()
    )
    past = (
        doctor.appointments.filter(
            Appointment.status.in_(
                [Appointment.STATUS_COMPLETED, Appointment.STATUS_CANCELLED]
            )
        )
        .order_by(Appointment.scheduled_at.desc())
        .all()
    )
    return render_template(
        "doctor/appointments.html", upcoming=upcoming, past=past
    )