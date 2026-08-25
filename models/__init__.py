"""Model package. Import every model here so `db.create_all()` sees them."""

from models.role import Role
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.medical_history import MedicalHistory
from models.prediction import Prediction
from models.medical_report import MedicalReport
from models.appointment import Appointment
from models.notification import Notification
from models.audit_log import AuditLog
from models.phone_otp import PhoneOTP

__all__ = [
    "Role",
    "User",
    "Patient",
    "Doctor",
    "MedicalHistory",
    "Prediction",
    "MedicalReport",
    "Appointment",
    "Notification",
    "AuditLog",
    "PhoneOTP",
]
