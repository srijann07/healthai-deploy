"""Appointment booking and status workflow.

Patients book against their assigned doctor; doctors confirm, complete or
cancel. Both sides are notified of every change.
"""

from datetime import datetime, timedelta, timezone

from extensions import db
from models.appointment import Appointment
from models.doctor import Doctor
from models.notification import Notification
from models.patient import Patient
from services import validation_service as v
from services.audit_service import log_action
from services.notification_service import notify


class AppointmentError(Exception):
    """Raised for appointment flows that must stop the request."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


_VALID_TRANSITIONS = {
    Appointment.STATUS_PENDING: (Appointment.STATUS_CONFIRMED, Appointment.STATUS_COMPLETED, Appointment.STATUS_CANCELLED),
    Appointment.STATUS_CONFIRMED: (Appointment.STATUS_COMPLETED, Appointment.STATUS_CANCELLED),
    Appointment.STATUS_COMPLETED: (),
    Appointment.STATUS_CANCELLED: (),
}


def book_appointment(patient: Patient, scheduled_at_raw: str, reason: str) -> Appointment:
    """Create a pending appointment with the patient's assigned doctor."""
    reason = v.validate_optional_text(reason or "", "Reason", max_length=255)
    if not reason:
        raise AppointmentError("Please describe the reason for the visit.")

    if not patient.assigned_doctor:
        raise AppointmentError(
            "You don't have an assigned doctor yet. Please contact support.",
            status_code=409,
        )

    try:
        scheduled = datetime.strptime(scheduled_at_raw, "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError):
        raise AppointmentError(
            "Please pick a date and time for the appointment "
            "(format YYYY-MM-DD HH:MM)."
        )

    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if scheduled <= now:
        raise AppointmentError("Appointment time must be in the future.")
    if scheduled > now + timedelta(days=90):
        raise AppointmentError("Appointments can be booked up to 90 days ahead.")

    appointment = Appointment(
        patient=patient,
        doctor=patient.assigned_doctor,
        scheduled_at=scheduled,
        reason=reason,
        status=Appointment.STATUS_PENDING,
    )
    db.session.add(appointment)
    db.session.commit()

    notify(
        patient.assigned_doctor.user_id,
        "New appointment request",
        f"{patient.user.full_name if patient.user else 'A patient'} requested "
        f"a visit on {scheduled.strftime('%d %b %Y, %H:%M')}.",
        Notification.CATEGORY_SYSTEM,
        link="/doctor/appointments",
    )
    log_action(
        "appointment_booked",
        user_id=patient.user_id,
        entity="appointment",
        entity_id=appointment.id,
    )
    return appointment


def set_appointment_status(
    appointment: Appointment, new_status: str, actor_user
) -> Appointment:
    """Transition an appointment to a valid next status and notify the
    other party involved."""
    allowed = _VALID_TRANSITIONS.get(appointment.status, ())
    if new_status not in allowed:
        raise AppointmentError("That action is not valid for this appointment.")

    appointment.status = new_status
    db.session.commit()

    is_doctor = (
        actor_user.doctor_profile.id
        if actor_user and actor_user.doctor_profile
        else None
    ) == appointment.doctor_id
    # Notify the party that did not perform the action.
    if is_doctor:
        notify(
            appointment.patient.user_id,
            f"Appointment {new_status}",
            f"Your appointment on "
            f"{appointment.scheduled_at.strftime('%d %b %Y, %H:%M')} was "
            f"{new_status} by your doctor.",
            "system",
            link="/patient/appointments",
        )
    else:
        notify(
            appointment.doctor.user_id,
            f"Appointment {new_status}",
            f"The appointment on "
            f"{appointment.scheduled_at.strftime('%d %b %Y, %H:%M')} was "
            f"{new_status} by the patient.",
            "system",
            link="/doctor/appointments",
        )
    log_action(
        f"appointment_{new_status}",
        user_id=actor_user.id if actor_user else None,
        entity="appointment",
        entity_id=appointment.id,
    )
    return appointment