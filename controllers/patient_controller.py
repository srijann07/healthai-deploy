"""Request handling for the patient's own profile, health information and reports."""

from datetime import datetime

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from extensions import db
from middlewares.auth_middleware import get_current_user, role_required
from models.appointment import Appointment
from models.medical_report import MedicalReport
from models.prediction import Prediction
from models.role import Role
from services import (
    appointment_service,
    health_analysis,
    profile_service,
    report_service,
)
from services.appointment_service import AppointmentError
from services.audit_service import log_action
from services.profile_service import ProfileError
from services.prediction_service import PredictionError, run_assessment
from services.report_service import ReportError
from services.validation_service import ValidationError

_HEALTH_SECTIONS = ("basic", "history")


def _fmt_num(value) -> str:
    if value is None:
        return ""
    return str(value) if isinstance(value, int) else f"{value:g}"


def _health_form_data(patient, history, submitted=None) -> dict:
    """Current values for the health page, overlaid with a failed submission."""
    history = history or {}
    values = {
        "date_of_birth": (
            patient.date_of_birth.strftime("%Y-%m-%d")
            if patient and patient.date_of_birth
            else ""
        ),
        "gender": (patient.gender if patient else "") or "",
        "blood_group": (patient.blood_group if patient else "") or "",
        "height_cm": _fmt_num(patient.height_cm if patient else None),
        "weight_kg": _fmt_num(patient.weight_kg if patient else None),
        "address": (patient.address if patient else "") or "",
        "emergency_contact": (patient.emergency_contact if patient else "") or "",
        "allergies": history.get("allergies", ""),
        "chronic_conditions": history.get("chronic_conditions", ""),
        "previous_diseases": history.get("previous_diseases", ""),
        "current_medications": history.get("current_medications", ""),
        "family_history": history.get("family_history", ""),
        "smoking_status": history.get("smoking_status", ""),
        "alcohol_consumption": history.get("alcohol_consumption", ""),
        "exercise_frequency": history.get("exercise_frequency", ""),
    }
    if submitted is not None:
        values.update({k: (v or "") for k, v in submitted.items() if k in values})
    return values


def _history_data(patient) -> dict:
    history = patient.medical_history if patient else None
    if not history:
        return {}
    return {
        "allergies": history.allergies or "",
        "chronic_conditions": history.chronic_conditions or "",
        "previous_diseases": history.previous_diseases or "",
        "current_medications": history.current_medications or "",
        "family_history": history.family_history or "",
        "smoking_status": history.smoking_status or "",
        "alcohol_consumption": history.alcohol_consumption or "",
        "exercise_frequency": history.exercise_frequency or "",
    }


@role_required(Role.PATIENT)
def profile_page():
    """View and edit the patient's own account details."""
    user = get_current_user()

    if request.method == "POST":
        try:
            profile_service.update_personal_details(user, request.form.to_dict())
        except ValidationError as exc:
            flash(str(exc), "danger")
            return (
                render_template(
                    "patient/profile.html",
                    values=request.form.to_dict(),
                    email=user.email,
                ),
                400,
            )
        flash("Your profile was updated.", "success")
        return redirect(url_for("patient.profile_page"))

    return render_template(
        "patient/profile.html",
        values={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone or "",
        },
        email=user.email,
    )


@role_required(Role.PATIENT)
def health_page():
    """View and edit basic health information and medical history."""
    user = get_current_user()
    patient = user.patient_profile

    if request.method == "POST":
        section = request.form.get("section")
        if section not in _HEALTH_SECTIONS:
            flash("Unknown form submission.", "danger")
            return redirect(url_for("patient.health_page"))

        history = patient.medical_history if patient else None
        try:
            if section == "basic":
                profile_service.update_health_information(patient, request.form)
            else:
                profile_service.update_medical_history(patient, request.form)
        except ValidationError as exc:
            flash(str(exc), "danger")
            return (
                render_template(
                    "patient/health.html",
                    patient=patient,
                    values=_health_form_data(
                        patient, _history_data(patient), request.form.to_dict()
                    ),
                    active_section=section,
                ),
                400,
            )
        flash(
            "Health information was saved." if section == "basic"
            else "Medical history was saved.",
            "success",
        )
        return redirect(url_for("patient.health_page"))

    return render_template(
        "patient/health.html",
        patient=patient,
        values=_health_form_data(patient, _history_data(patient)),
        active_section="",
    )


@role_required(Role.PATIENT)
def change_password_page():
    """Change the current account password."""
    user = get_current_user()

    if request.method == "POST":
        data = request.form.to_dict()
        try:
            profile_service.change_password(
                user,
                data.get("current_password", ""),
                data.get("new_password", ""),
                data.get("confirm_password", ""),
            )
        except (ProfileError, ValidationError) as exc:
            flash(str(exc), "danger")
            return render_template("patient/change_password.html"), 400

        flash("Your password was changed.", "success")
        return redirect(url_for("patient.profile_page"))

    return render_template("patient/change_password.html")


# ----------------------------------------------------------------------
# Medical reports
# ----------------------------------------------------------------------

def _get_own_report(report_id: int) -> MedicalReport | None:
    """Return a report only if it belongs to the currently logged-in patient."""
    user = get_current_user()
    report = db.session.get(MedicalReport, report_id)
    if report is None or report.patient_id != user.patient_profile.id:
        return None
    return report


@role_required(Role.PATIENT)
def reports_page():
    """List the patient's reports and accept new uploads."""
    user = get_current_user()
    patient = user.patient_profile

    if request.method == "POST":
        try:
            report_service.save_report(
                patient,
                request.files.get("report_file"),
                request.form.get("description", ""),
            )
        except (ReportError, ValidationError) as exc:
            flash(str(exc), "danger")
            return redirect(url_for("patient.reports_page"))
        flash("Your report was uploaded.", "success")
        return redirect(url_for("patient.reports_page"))

    page = request.args.get("page", 1, type=int)
    pagination = (
        patient.medical_reports.order_by(MedicalReport.uploaded_at.desc())
        .paginate(page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False)
    )
    return render_template("patient/reports.html", pagination=pagination)


@role_required(Role.PATIENT)
def download_report(report_id: int):
    """Download one of the patient's own report files (local or cloud)."""
    report = _get_own_report(report_id)
    if report is None:
        abort(404)

    log_action(
        "report_downloaded",
        user_id=get_current_user().id,
        entity="medical_report",
        entity_id=report.id,
        details=report.original_filename,
    )
    return report_service.get_report_download_response(report)


@role_required(Role.PATIENT)
def delete_report_page(report_id: int):
    """Delete one of the patient's own reports (record + stored file)."""
    report = _get_own_report(report_id)
    if report is None:
        abort(404)
    report_service.delete_report(report)
    flash("The report was deleted.", "success")
    return redirect(url_for("patient.reports_page"))


# --- JSON API -----------------------------------------------------------

@role_required(Role.PATIENT)
def api_list_reports():
    """Return the patient's report list as JSON."""
    user = get_current_user()
    reports = user.patient_profile.medical_reports.order_by(
        MedicalReport.uploaded_at.desc()
    ).all()
    return jsonify(
        {
            "success": True,
            "reports": [
                {
                    "id": r.id,
                    "original_filename": r.original_filename,
                    "file_type": r.file_type,
                    "file_size": r.file_size,
                    "size_display": r.size_display,
                    "description": r.description,
                    "uploaded_at": r.uploaded_at.isoformat(),
                }
                for r in reports
            ],
        }
    )


@role_required(Role.PATIENT)
def api_upload_report():
    """Accept a multipart report upload and return the stored record."""
    user = get_current_user()
    try:
        report = report_service.save_report(
            user.patient_profile,
            request.files.get("report_file"),
            (request.form.get("description") or ""),
        )
    except (ReportError, ValidationError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return (
        jsonify(
            {
                "success": True,
                "report": {
                    "id": report.id,
                    "original_filename": report.original_filename,
                    "file_type": report.file_type,
                    "file_size": report.file_size,
                    "uploaded_at": report.uploaded_at.isoformat(),
                },
            }
        ),
        201,
    )


@role_required(Role.PATIENT)
def api_delete_report(report_id: int):
    """Delete the patient's own report."""
    report = _get_own_report(report_id)
    if report is None:
        return jsonify({"success": False, "error": "Report not found."}), 404
    report_service.delete_report(report)
    return jsonify({"success": True, "message": "Report deleted."})


# ----------------------------------------------------------------------
# AI health check (assessments) and predictions
# ----------------------------------------------------------------------

def _assess_form_values(patient):
    """Prefill the assessment form from the patient's profile + history."""
    history = patient.medical_history if patient else None
    return {
        "age": patient.age if patient and patient.age else "",
        "gender": patient.gender if patient else "",
        "systolic_bp": "",
        "diastolic_bp": "",
        "heart_rate": "",
        "blood_sugar": "",
        "body_temperature": "",
        "oxygen_level": "",
        "chronic_conditions": (history.chronic_conditions or "") if history else "",
        "smoking_status": (history.smoking_status or "") if history else "",
    }


@role_required(Role.PATIENT)
def assess_page():
    """Run an AI health check based on symptoms + habits + vitals."""
    user = get_current_user()
    patient = user.patient_profile

    if request.method == "POST":
        try:
            prediction = run_assessment(patient, request.form)
        except (PredictionError, ValidationError) as exc:
            flash(str(exc), "danger")
            return render_template(
                "patient/assess.html",
                symptoms=health_analysis.SYMPTOM_LABELS,
                values=request.form.to_dict(),
            ), 400
        flash(
            f"Your AI health check is complete — risk level "
            f"{prediction.risk_level}. Your doctor will review it shortly.",
            "success",
        )
        return redirect(url_for("patient.prediction_detail_page", prediction_id=prediction.id))

    return render_template(
        "patient/assess.html",
        symptoms=health_analysis.SYMPTOM_LABELS,
        values=_assess_form_values(patient),
    )


@role_required(Role.PATIENT)
def predictions_page():
    """List the patient's AI assessments with their review status."""
    user = get_current_user()
    patient = user.patient_profile
    status_filter = request.args.get("status", "all")
    query = patient.predictions if patient else None
    if query is None:
        return render_template("patient/predictions.html", pagination=None, status_filter=status_filter)
    if status_filter in (
        Prediction.STATUS_PENDING,
        Prediction.STATUS_APPROVED,
        Prediction.STATUS_REJECTED,
    ):
        query = query.filter_by(status=status_filter)
    pagination = (
        query.order_by(Prediction.created_at.desc())
        .paginate(
            page=request.args.get("page", 1, type=int),
            per_page=current_app.config["ITEMS_PER_PAGE"],
            error_out=False,
        )
    )
    return render_template(
        "patient/predictions.html", pagination=pagination, status_filter=status_filter
    )


@role_required(Role.PATIENT)
def prediction_detail_page(prediction_id: int):
    """View one assessment and any doctor review of it."""
    user = get_current_user()
    prediction = db.session.get(Prediction, prediction_id)
    if prediction is None or prediction.patient_id != user.patient_profile.id:
        abort(404)
    return render_template("patient/prediction_detail.html", prediction=prediction)


# ----------------------------------------------------------------------
# Assigned doctor
# ----------------------------------------------------------------------

@role_required(Role.PATIENT)
def assigned_doctor_page():
    """Show the patient's assigned doctor and their public details."""
    user = get_current_user()
    patient = user.patient_profile
    return render_template("patient/doctor.html", doctor=patient.assigned_doctor)


# ----------------------------------------------------------------------
# Appointments
# ----------------------------------------------------------------------

@role_required(Role.PATIENT)
def appointments_page():
    """List the patient's appointments and accept new bookings."""
    user = get_current_user()
    patient = user.patient_profile

    if request.method == "POST":
        try:
            appointment_service.book_appointment(
                patient,
                request.form.get("scheduled_at", ""),
                request.form.get("reason", ""),
            )
        except AppointmentError as exc:
            flash(str(exc), "danger")
            return (
                render_template(
                    "patient/appointments.html",
                    appointments=patient.appointments.order_by(
                        Appointment.scheduled_at.desc()
                    ).all(),
                    values=request.form.to_dict(),
                ),
                exc.status_code,
            )
        flash("Appointment requested. You will be notified when it is confirmed.", "success")
        return redirect(url_for("patient.appointments_page"))

    appointments = (
        patient.appointments.order_by(Appointment.scheduled_at.desc()).all()
    )
    return render_template(
        "patient/appointments.html",
        appointments=appointments,
        values={"scheduled_at": "", "reason": ""},
    )


@role_required(Role.PATIENT)
def cancel_appointment_page(appointment_id: int):
    """Cancel one of the patient's own appointments."""
    user = get_current_user()
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None or appointment.patient_id != user.patient_profile.id:
        abort(404)
    try:
        appointment_service.set_appointment_status(appointment, Appointment.STATUS_CANCELLED, user)
    except AppointmentError as exc:
        flash(str(exc), "danger")
    else:
        flash("Your appointment was cancelled.", "success")
    return redirect(url_for("patient.appointments_page"))