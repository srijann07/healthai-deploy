"""Request handling for the admin module.

Admins get full platform control: user/patient/doctor management, all
predictions, appointments, medical-report (file) oversight, the audit trail
and a broadcast-announcement tool.
"""

from datetime import datetime, timedelta

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from extensions import db
from middlewares.auth_middleware import get_current_user, role_required
from models.appointment import Appointment
from models.audit_log import AuditLog
from models.doctor import Doctor
from models.medical_report import MedicalReport
from models.notification import Notification
from models.patient import Patient
from models.prediction import Prediction
from models.role import Role
from models.user import User
from services import appointment_service, report_service, validation_service as v
from services.appointment_service import AppointmentError
from services.audit_service import log_action
from services.notification_service import notify


def _admin() -> User:
    """The authenticated admin (guaranteed by role_required)."""
    return get_current_user()


def _admin_count() -> int:
    return User.query.join(Role, User.role_id == Role.id).filter(
        Role.name == Role.ADMIN
    ).count()


def _page() -> int:
    return request.args.get("page", 1, type=int)


def _latest_by_patient(patients) -> dict[int, Prediction]:
    """Latest prediction per patient, one query."""
    if not patients:
        return {}
    patient_ids = [p.id for p in patients]
    rows = (
        db.session.query(Prediction)
        .filter(Prediction.patient_id.in_(patient_ids))
        .order_by(Prediction.patient_id, Prediction.created_at.desc())
        .all()
    )
    latest, seen = {}, set()
    for row in rows:
        if row.patient_id not in seen:
            latest[row.patient_id] = row
            seen.add(row.patient_id)
    return latest


def _unassign_from_doctor(doctor_id: int) -> None:
    Patient.query.filter_by(assigned_doctor_id=doctor_id).update(
        {"assigned_doctor_id": None}
    )


def _delete_user(target: User) -> None:
    """Remove a user and all their records, without breaking foreign keys."""
    doctor = target.doctor_profile
    if doctor is not None:
        _unassign_from_doctor(doctor.id)
        Prediction.query.filter_by(doctor_id=doctor.id).update({"doctor_id": None})
        Appointment.query.filter_by(doctor_id=doctor.id).delete()
    AuditLog.query.filter_by(user_id=target.id).update({"user_id": None})
    db.session.delete(target)
    db.session.commit()


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def dashboard():
    """Platform overview: counts, risk distribution, recent signups, activity."""
    now_utc = datetime.utcnow()
    day_ago = now_utc - timedelta(days=1)
    month_ago = now_utc - timedelta(days=30)

    risk_counts = {}
    for level in Prediction.RISK_LEVELS:
        risk_counts[level] = Prediction.query.filter_by(risk_level=level).count()

    stats = {
        "patients": Patient.query.count(),
        "doctors": Doctor.query.count(),
        "users": User.query.count(),
        "predictions": Prediction.query.count(),
        "high_risk": Prediction.query.filter(
            Prediction.risk_level.in_(["High", "Critical"])
        ).count(),
        "reports": MedicalReport.query.count(),
        "appointments": Appointment.query.count(),
        "pending_reviews": Prediction.query.filter_by(
            status=Prediction.STATUS_PENDING
        ).count(),
        "pending_appointments": Appointment.query.filter_by(
            status=Appointment.STATUS_PENDING
        ).count(),
        "new_users_30d": User.query.filter(User.created_at >= month_ago).count(),
        "active_today": User.query.filter(User.created_at >= day_ago).count(),
    }
    recent_users = (
        User.query.order_by(User.created_at.desc()).limit(5).all()
    )
    recent_activity = (
        AuditLog.query.order_by(AuditLog.created_at.desc()).limit(6).all()
    )
    return render_template(
        "dashboard/admin.html",
        stats=stats,
        risk_counts=risk_counts,
        risk_total=max(sum(risk_counts.values()), 1),
        recent_users=recent_users,
        recent_activity=recent_activity,
    )


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def users_page():
    """Every account on the platform with search + role/status filters."""
    search = (request.args.get("q") or "").strip()
    role_filter = request.args.get("role", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = User.query.join(Role, User.role_id == Role.id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
            )
        )
    if role_filter in Role.ALL:
        query = query.filter(Role.name == role_filter)
    if status_filter == "suspended":
        query = query.filter(User.is_suspended.is_(True))
    elif status_filter == "active":
        query = query.filter(User.is_active.is_(True), User.is_suspended.is_(False))

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=_page(),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    return render_template(
        "admin/users.html",
        pagination=pagination,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        roles=Role.ALL,
    )


@role_required(Role.ADMIN)
def user_toggle(user_id: int):
    """Suspend / reactivate an account."""
    target = db.session.get(User, user_id)
    if target is None:
        abort(404)
    if target.id == _admin().id:
        flash("You can't suspend your own account.", "danger")
        return redirect(url_for("admin.users_page"))

    target.is_suspended = not target.is_suspended
    db.session.commit()
    if target.is_suspended:
        log_action(
            "user_suspended",
            user_id=_admin().id,
            entity="user",
            entity_id=target.id,
            details=target.email,
        )
        notify(
            target.id,
            "Account suspended",
            "Your account has been suspended by an administrator. "
            "Contact support if you believe this is a mistake.",
            Notification.CATEGORY_SYSTEM,
        )
        flash(f"{target.full_name} has been suspended.", "success")
    else:
        log_action(
            "user_reactivated",
            user_id=_admin().id,
            entity="user",
            entity_id=target.id,
            details=target.email,
        )
        notify(
            target.id,
            "Account reactivated",
            "Your account has been reactivated. Welcome back!",
            Notification.CATEGORY_SYSTEM,
        )
        flash(f"{target.full_name} has been reactivated.", "success")
    return redirect(request.referrer or url_for("admin.users_page"))


@role_required(Role.ADMIN)
def user_change_role(user_id: int):
    """Change an account's role (creates missing doctor/patient profiles)."""
    target = db.session.get(User, user_id)
    new_role = request.form.get("role", "")
    if target is None or new_role not in Role.ALL:
        abort(404)
    if target.id == _admin().id:
        flash("You can't change your own role.", "danger")
        return redirect(url_for("admin.users_page"))
    if target.has_role(Role.ADMIN) and _admin_count() <= 1:
        flash("Can't demote the last remaining administrator.", "danger")
        return redirect(url_for("admin.users_page"))
    if new_role == target.role_name:
        flash("That user already has this role.", "warning")
        return redirect(url_for("admin.users_page"))

    role = Role.get_by_name(new_role)
    if role is None:
        abort(404)
    target.role = role
    if new_role == Role.DOCTOR and target.doctor_profile is None:
        target.doctor_profile = Doctor(specialization="General Practitioner")
    if new_role == Role.PATIENT and target.patient_profile is None:
        target.patient_profile = Patient()
    db.session.commit()

    log_action(
        "role_changed",
        user_id=_admin().id,
        entity="user",
        entity_id=target.id,
        details=f"{target.email} -> {new_role}",
    )
    notify(
        target.id,
        "Role updated",
        f"Your account role is now {new_role.capitalize()}.",
        Notification.CATEGORY_SYSTEM,
    )
    flash(f"{target.full_name} is now a {new_role.capitalize()}.", "success")
    return redirect(request.referrer or url_for("admin.users_page"))


@role_required(Role.ADMIN)
def user_delete(user_id: int):
    """Permanently delete an account and everything attached to it."""
    target = db.session.get(User, user_id)
    if target is None:
        abort(404)
    if target.id == _admin().id:
        flash("You can't delete your own account.", "danger")
        return redirect(url_for("admin.users_page"))
    if target.has_role(Role.ADMIN) and _admin_count() <= 1:
        flash("Can't delete the last remaining administrator.", "danger")
        return redirect(url_for("admin.users_page"))

    email = target.email
    _delete_user(target)
    log_action(
        "user_deleted",
        user_id=_admin().id,
        entity="user",
        entity_id=target.id,
        details=email,
    )
    flash(f"Deleted account {email} and all associated data.", "success")
    return redirect(request.referrer or url_for("admin.users_page"))


# --------------------------------------------------------------------------
# Patients
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def patients_page():
    """All patients with search, latest-risk and assignment filters."""
    query = Patient.query.join(User, User.id == Patient.user_id)

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

    doctor_filter = request.args.get("doctor", "")
    if doctor_filter == "none":
        query = query.filter(Patient.assigned_doctor_id.is_(None))
    elif doctor_filter.isdigit():
        query = query.filter(Patient.assigned_doctor_id == int(doctor_filter))

    pagination = query.order_by(User.first_name.asc(), User.last_name.asc()).paginate(
        page=_page(),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    return render_template(
        "admin/patients.html",
        pagination=pagination,
        search=search,
        risk=risk,
        doctor_filter=doctor_filter,
        risk_levels=Prediction.RISK_LEVELS,
        latest_by_patient=_latest_by_patient(pagination.items),
        doctors=Doctor.query.order_by(Doctor.specialization.asc()).all(),
    )


@role_required(Role.ADMIN)
def patient_detail_page(patient_id: int):
    """Full patient record: profile, history, assessments, reports, appointments."""
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        abort(404)
    predictions = (
        patient.predictions.order_by(Prediction.created_at.desc()).all()
    )
    reports = patient.medical_reports.order_by(
        MedicalReport.uploaded_at.desc()
    ).all()
    appointments = patient.appointments.order_by(
        Appointment.scheduled_at.desc()
    ).all()
    return render_template(
        "admin/patient_detail.html",
        patient=patient,
        predictions=predictions,
        reports=reports,
        appointments=appointments,
        doctors=Doctor.query.order_by(Doctor.specialization.asc()).all(),
    )


@role_required(Role.ADMIN)
def patient_assign_doctor(patient_id: int):
    """Assign (or unassign) a doctor for one patient."""
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        abort(404)

    raw = request.form.get("doctor_id", "").strip()
    if not raw:
        if patient.assigned_doctor_id is not None:
            old = patient.assigned_doctor
            patient.assigned_doctor = None
            db.session.commit()
            log_action(
                "doctor_unassigned",
                user_id=_admin().id,
                entity="patient",
                entity_id=patient.id,
                details=f"doctor_id={old.id}" if old else None,
            )
            if old is not None:
                notify(
                    old.user_id,
                    "Patient unassigned",
                    f"{patient.user.full_name} is no longer assigned to you.",
                    Notification.CATEGORY_PROFILE,
                )
            flash("Doctor assignment removed.", "success")
        return redirect(url_for("admin.patient_detail_page", patient_id=patient.id))

    doctor = db.session.get(Doctor, int(raw)) if raw.isdigit() else None
    if doctor is None:
        flash("Choose a valid doctor.", "danger")
        return redirect(url_for("admin.patient_detail_page", patient_id=patient.id))

    patient.assigned_doctor = doctor
    db.session.commit()
    log_action(
        "doctor_assigned",
        user_id=_admin().id,
        entity="patient",
        entity_id=patient.id,
        details=f"doctor_id={doctor.id}",
    )
    notify(
        patient.user_id,
        "Doctor assigned",
        f"Dr. {doctor.user.full_name} is now your assigned doctor.",
        Notification.CATEGORY_PROFILE,
        link="/patient/doctor",
    )
    notify(
        doctor.user_id,
        "New patient assigned",
        f"{patient.user.full_name} has been assigned to you by an administrator.",
        Notification.CATEGORY_PROFILE,
        link="/doctor/patients",
    )
    flash(f"Assigned Dr. {doctor.user.full_name} to {patient.user.full_name}.", "success")
    return redirect(url_for("admin.patient_detail_page", patient_id=patient.id))


# --------------------------------------------------------------------------
# Doctors
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def doctors_page():
    """All doctors with workload stats and an account-creation form."""
    doctors = Doctor.query.order_by(Doctor.created_at.desc()).all()
    pending_by_doctor = {}
    patient_count_by_doctor = {}
    for doctor in doctors:
        pending_by_doctor[doctor.id] = (
            Prediction.query.filter(
                Prediction.doctor_id == doctor.id,
                Prediction.status == Prediction.STATUS_PENDING,
            ).count()
        )
        patient_count_by_doctor[doctor.id] = (
            Patient.query.filter_by(assigned_doctor_id=doctor.id).count()
        )
    return render_template(
        "admin/doctors.html",
        doctors=doctors,
        pending_by_doctor=pending_by_doctor,
        patient_count_by_doctor=patient_count_by_doctor,
    )


@role_required(Role.ADMIN)
def doctor_create():
    """Create a doctor account with its profile, ready to log in."""
    try:
        first_name = v.validate_name(
            v.require(request.form.get("first_name", ""), "First name"), "First name"
        )
        last_name = v.validate_name(
            v.require(request.form.get("last_name", ""), "Last name"), "Last name"
        )
        email = v.validate_email_address(
            v.require(request.form.get("email", ""), "Email")
        )
        password = v.validate_password_strength(
            v.require(request.form.get("password", ""), "Password")
        )
        specialization = v.clean_str(
            v.require(request.form.get("specialization", ""), "Specialization"),
            max_length=100,
        )
        hospital = v.validate_optional_text(
            request.form.get("hospital", ""), "Hospital", max_length=150
        ) or None
        license_number = v.validate_optional_text(
            request.form.get("license_number", ""), "License number", max_length=60
        ) or None
        years_experience = v.validate_optional_number(
            request.form.get("years_experience", ""),
            "Years of experience",
            minimum=0,
            maximum=60,
        ) or 0
        bio = v.validate_optional_text(
            request.form.get("bio", ""), "Bio", max_length=1000
        ) or None
    except (v.ValidationError, ValueError) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin.doctors_page"))

    if User.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "danger")
        return redirect(url_for("admin.doctors_page"))
    if license_number and Doctor.query.filter_by(license_number=license_number).first():
        flash("That license number is already registered.", "danger")
        return redirect(url_for("admin.doctors_page"))

    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=Role.get_by_name(Role.DOCTOR),
    )
    user.set_password(password)
    user.doctor_profile = Doctor(
        specialization=specialization,
        license_number=license_number,
        years_experience=years_experience,
        hospital=hospital,
        bio=bio,
    )
    db.session.add(user)
    db.session.commit()

    log_action(
        "doctor_created",
        user_id=_admin().id,
        entity="doctor",
        entity_id=user.doctor_profile.id,
        details=email,
    )
    notify(
        user.id,
        "Account created",
        "An administrator created your doctor account. Welcome aboard!",
        Notification.CATEGORY_SYSTEM,
        link="/doctor/dashboard",
    )
    flash(f"Doctor account created for {email}.", "success")
    return redirect(url_for("admin.doctors_page"))


@role_required(Role.ADMIN)
def doctor_toggle_availability(doctor_id: int):
    """Flip a doctor's availability for new patient assignments."""
    doctor = db.session.get(Doctor, doctor_id)
    if doctor is None:
        abort(404)
    doctor.is_available = not doctor.is_available
    db.session.commit()
    log_action(
        "doctor_availability_changed",
        user_id=_admin().id,
        entity="doctor",
        entity_id=doctor.id,
        details=f"is_available={doctor.is_available}",
    )
    state = "available" if doctor.is_available else "unavailable"
    flash(f"Dr. {doctor.user.full_name} is now {state}.", "success")
    return redirect(request.referrer or url_for("admin.doctors_page"))


@role_required(Role.ADMIN)
def doctor_delete(doctor_id: int):
    """Delete a doctor account (reassigns nothing; unassigns their patients)."""
    doctor = db.session.get(Doctor, doctor_id)
    if doctor is None or doctor.user is None:
        abort(404)
    email = doctor.user.email
    _delete_user(doctor.user)
    log_action(
        "doctor_deleted",
        user_id=_admin().id,
        entity="doctor",
        entity_id=doctor.id,
        details=email,
    )
    flash(f"Deleted doctor account {email}. Their patients are now unassigned.", "success")
    return redirect(url_for("admin.doctors_page"))


# --------------------------------------------------------------------------
# Predictions
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def predictions_page():
    """Every AI assessment, with status and risk filters."""
    tab = request.args.get("tab", "all")
    query = Prediction.query
    if tab == "pending":
        query = query.filter(Prediction.status == Prediction.STATUS_PENDING)
        tab = "pending"
    elif tab == "reviewed":
        query = query.filter(
            Prediction.status.in_(
                [Prediction.STATUS_APPROVED, Prediction.STATUS_REJECTED]
            )
        )
        tab = "reviewed"
    else:
        tab = "all"

    risk = request.args.get("risk", "")
    if risk in Prediction.RISK_LEVELS:
        query = query.filter(Prediction.risk_level == risk)

    pagination = query.order_by(Prediction.created_at.desc()).paginate(
        page=_page(),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    return render_template(
        "admin/predictions.html",
        pagination=pagination,
        tab=tab,
        risk=risk,
        risk_levels=Prediction.RISK_LEVELS,
    )


# --------------------------------------------------------------------------
# Appointments
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def appointments_page():
    """All appointments across the platform, with status actions."""
    status = request.args.get("status", "").strip()
    query = Appointment.query
    if status in {
        Appointment.STATUS_PENDING,
        Appointment.STATUS_CONFIRMED,
        Appointment.STATUS_COMPLETED,
        Appointment.STATUS_CANCELLED,
    }:
        query = query.filter(Appointment.status == status)
    else:
        status = ""

    if request.method == "POST":
        return _appointment_status_post()

    pagination = query.order_by(Appointment.scheduled_at.desc()).paginate(
        page=_page(),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    return render_template(
        "admin/appointments.html", pagination=pagination, status=status
    )


def _appointment_status_post():
    appointment = db.session.get(
        Appointment, request.form.get("appointment_id", type=int)
    )
    action = request.form.get("action", "")
    status_map = {
        "confirm": Appointment.STATUS_CONFIRMED,
        "complete": Appointment.STATUS_COMPLETED,
        "cancel": Appointment.STATUS_CANCELLED,
    }
    if appointment is None:
        abort(404)
    try:
        appointment_service.set_appointment_status(
            appointment, status_map.get(action, ""), _admin()
        )
    except AppointmentError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Appointment {action}ed.", "success")
    return redirect(request.referrer or url_for("admin.appointments_page"))


# --------------------------------------------------------------------------
# Medical reports (file oversight)
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def reports_page():
    """Every uploaded file on the platform, with download/delete oversight."""
    query = MedicalReport.query.join(Patient, Patient.id == MedicalReport.patient_id)
    query = query.join(User, User.id == Patient.user_id)
    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                MedicalReport.original_filename.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
            )
        )
    pagination = query.order_by(MedicalReport.uploaded_at.desc()).paginate(
        page=_page(),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    total_size = db.session.query(db.func.coalesce(db.func.sum(MedicalReport.file_size), 0)).scalar() or 0
    return render_template(
        "admin/reports.html",
        pagination=pagination,
        search=search,
        total_size=total_size,
    )


@role_required(Role.ADMIN)
def report_download(report_id: int):
    """Download any uploaded medical file (admin oversight, local or cloud)."""
    report = db.session.get(MedicalReport, report_id)
    if report is None:
        abort(404)
    log_action(
        "report_downloaded",
        user_id=_admin().id,
        entity="medical_report",
        entity_id=report.id,
        details=report.original_filename,
    )
    return report_service.get_report_download_response(report)


@role_required(Role.ADMIN)
def report_delete(report_id: int):
    """Delete an uploaded file (record + stored file)."""
    report = db.session.get(MedicalReport, report_id)
    if report is None:
        abort(404)
    name = report.original_filename
    report_service.delete_report(report)
    flash(f"Deleted report {name}.", "success")
    return redirect(request.referrer or url_for("admin.reports_page"))


# --------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def audit_page():
    """Security-relevant actions across the platform."""
    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=_page(),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    return render_template("admin/audit.html", pagination=pagination)


# --------------------------------------------------------------------------
# Announcements
# --------------------------------------------------------------------------


@role_required(Role.ADMIN)
def announce_page():
    """Send a broadcast notification to every active user."""
    if request.method == "POST":
        try:
            title = v.clean_str(
                v.require(request.form.get("title", ""), "Title"), max_length=120
            )
            message = v.clean_str(
                v.require(request.form.get("message", ""), "Message"), max_length=255
            )
            category = request.form.get("category", Notification.CATEGORY_SYSTEM)
            if category not in {
                Notification.CATEGORY_SYSTEM,
                Notification.CATEGORY_PREDICTION,
                Notification.CATEGORY_REVIEW,
                Notification.CATEGORY_REPORT,
                Notification.CATEGORY_PROFILE,
            }:
                category = Notification.CATEGORY_SYSTEM
        except (v.ValidationError, ValueError) as exc:
            flash(str(exc), "danger")
            return render_template("admin/announce.html", values=request.form.to_dict())

        users = User.query.filter(
            User.is_active.is_(True), User.is_suspended.is_(False)
        ).all()
        notifications = [
            Notification(user_id=user.id, title=title, message=message, category=category)
            for user in users
        ]
        db.session.add_all(notifications)
        db.session.commit()
        log_action(
            "announcement_sent",
            user_id=_admin().id,
            entity="notification",
            details=f"title={title} recipients={len(users)}",
        )
        flash(f"Announcement sent to {len(users)} active users.", "success")
        return redirect(url_for("admin.announce_page"))

    recipients = User.query.filter(
        User.is_active.is_(True), User.is_suspended.is_(False)
    ).count()
    return render_template("admin/announce.html", values={}, recipients=recipients)
