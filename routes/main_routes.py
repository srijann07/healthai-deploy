"""Landing page, role dashboards and notification actions."""

from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from middlewares.auth_middleware import get_current_user, login_required, role_required
from models.notification import Notification
from models.prediction import Prediction
from models.role import Role
from services.notification_service import mark_all_read

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Public landing page; authenticated users go straight to their dashboard."""
    user = get_current_user()
    if user and user.can_login:
        return redirect(url_for("main.dashboard_redirect"))
    from models.user import User
    from models.medical_report import MedicalReport

    patient_role = Role.get_by_name(Role.PATIENT)
    doctor_role = Role.get_by_name(Role.DOCTOR)
    landing_stats = {
        "patients": User.query.filter_by(role_id=patient_role.id).count()
        if patient_role
        else 0,
        "doctors": User.query.filter_by(role_id=doctor_role.id).count()
        if doctor_role
        else 0,
        "predictions": Prediction.query.count(),
        "reports": MedicalReport.query.count(),
    }
    return render_template("index.html", landing_stats=landing_stats)


@main_bp.route("/dashboard")
@login_required
def dashboard_redirect():
    """Send the user to the dashboard for their role."""
    user = get_current_user()
    endpoint = {
        Role.PATIENT: "main.patient_dashboard",
        Role.DOCTOR: "main.doctor_dashboard",
        Role.ADMIN: "main.admin_dashboard",
    }.get(user.role_name, "main.index")
    return redirect(url_for(endpoint))


@main_bp.route("/patient/dashboard")
@role_required(Role.PATIENT)
def patient_dashboard():
    user = get_current_user()
    patient = user.patient_profile
    return render_template(
        "dashboard/patient.html",
        patient=patient,
        prediction_count=patient.predictions.count() if patient else 0,
        report_count=patient.medical_reports.count() if patient else 0,
        latest_prediction=(
            patient.predictions.order_by(db.desc("created_at")).first()
            if patient
            else None
        ),
    )


@main_bp.route("/doctor/dashboard")
@role_required(Role.DOCTOR)
def doctor_dashboard():
    user = get_current_user()
    doctor = user.doctor_profile
    from models.appointment import Appointment
    from services import doctor_service

    return render_template(
        "dashboard/doctor.html",
        doctor=doctor,
        patient_count=doctor_service.patient_count_for(doctor),
        pending_count=doctor_service.pending_reviews_for(doctor).count(),
        reviewed_count=(
            Prediction.query.filter(
                Prediction.doctor_id == doctor.id,
                Prediction.status.in_(
                    [Prediction.STATUS_APPROVED, Prediction.STATUS_REJECTED]
                ),
            ).count()
            if doctor
            else 0
        ),
        upcoming_appointments=(
            doctor.appointments.filter(
                Appointment.status.in_(
                    [Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]
                )
            ).count()
            if doctor
            else 0
        ),
    )


@main_bp.route("/admin/dashboard")
@role_required(Role.ADMIN)
def admin_dashboard():
    """Admin centre lives in the `admin` blueprint."""
    return redirect(url_for("admin.dashboard"))


@main_bp.route("/notifications")
@login_required
def notifications():
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    pagination = (
        user.notifications.order_by(Notification.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template("notifications.html", pagination=pagination)


@main_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def notifications_read_all():
    user = get_current_user()
    mark_all_read(user.id)
    return redirect(request.referrer or url_for("main.notifications"))
