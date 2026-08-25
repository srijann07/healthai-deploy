"""URL wiring for the doctor module. Logic lives in controllers/doctor_controller."""

from flask import Blueprint

from controllers import doctor_controller

doctor_bp = Blueprint("doctor", __name__)

doctor_bp.add_url_rule(
    "/doctor/patients",
    view_func=doctor_controller.patients_page,
    methods=["GET"],
    endpoint="patients_page",
)
doctor_bp.add_url_rule(
    "/doctor/patients/<int:patient_id>",
    view_func=doctor_controller.patient_detail_page,
    methods=["GET"],
    endpoint="patient_detail_page",
)
doctor_bp.add_url_rule(
    "/doctor/predictions",
    view_func=doctor_controller.predictions_page,
    methods=["GET"],
    endpoint="predictions_page",
)
doctor_bp.add_url_rule(
    "/doctor/predictions/<int:prediction_id>/review",
    view_func=doctor_controller.review_prediction_page,
    methods=["GET", "POST"],
    endpoint="review_prediction_page",
)
doctor_bp.add_url_rule(
    "/doctor/appointments",
    view_func=doctor_controller.appointments_page,
    methods=["GET", "POST"],
    endpoint="appointments_page",
)