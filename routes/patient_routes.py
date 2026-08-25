"""URL wiring for the patient module. Logic lives in controllers/patient_controller."""

from flask import Blueprint

from controllers import patient_controller

patient_bp = Blueprint("patient", __name__)

patient_bp.add_url_rule(
    "/patient/profile",
    view_func=patient_controller.profile_page,
    methods=["GET", "POST"],
    endpoint="profile_page",
)
patient_bp.add_url_rule(
    "/patient/health",
    view_func=patient_controller.health_page,
    methods=["GET", "POST"],
    endpoint="health_page",
)
patient_bp.add_url_rule(
    "/patient/change-password",
    view_func=patient_controller.change_password_page,
    methods=["GET", "POST"],
    endpoint="change_password_page",
)
patient_bp.add_url_rule(
    "/patient/reports",
    view_func=patient_controller.reports_page,
    methods=["GET", "POST"],
    endpoint="reports_page",
)
patient_bp.add_url_rule(
    "/patient/reports/<int:report_id>/download",
    view_func=patient_controller.download_report,
    methods=["GET"],
    endpoint="download_report",
)
patient_bp.add_url_rule(
    "/patient/reports/<int:report_id>/delete",
    view_func=patient_controller.delete_report_page,
    methods=["POST"],
    endpoint="delete_report",
)
patient_bp.add_url_rule(
    "/patient/assess",
    view_func=patient_controller.assess_page,
    methods=["GET", "POST"],
    endpoint="assess_health",
)
patient_bp.add_url_rule(
    "/patient/predictions",
    view_func=patient_controller.predictions_page,
    methods=["GET"],
    endpoint="predictions_page",
)
patient_bp.add_url_rule(
    "/patient/predictions/<int:prediction_id>",
    view_func=patient_controller.prediction_detail_page,
    methods=["GET"],
    endpoint="prediction_detail_page",
)
patient_bp.add_url_rule(
    "/patient/predictions/<int:prediction_id>/pdf",
    view_func=patient_controller.download_prediction_pdf,
    methods=["GET"],
    endpoint="download_prediction_pdf",
)
patient_bp.add_url_rule(
    "/patient/doctor",
    view_func=patient_controller.assigned_doctor_page,
    methods=["GET"],
    endpoint="assigned_doctor_page",
)
patient_bp.add_url_rule(
    "/patient/appointments",
    view_func=patient_controller.appointments_page,
    methods=["GET", "POST"],
    endpoint="appointments_page",
)
patient_bp.add_url_rule(
    "/patient/appointments/<int:appointment_id>/cancel",
    view_func=patient_controller.cancel_appointment_page,
    methods=["POST"],
    endpoint="cancel_appointment",
)

patient_api_bp = Blueprint("patient_api", __name__, url_prefix="/api")
patient_api_bp.add_url_rule(
    "/reports",
    view_func=patient_controller.api_list_reports,
    methods=["GET"],
    endpoint="list_reports",
)
patient_api_bp.add_url_rule(
    "/reports",
    view_func=patient_controller.api_upload_report,
    methods=["POST"],
    endpoint="upload_report",
)
patient_api_bp.add_url_rule(
    "/report/<int:report_id>",
    view_func=patient_controller.api_delete_report,
    methods=["DELETE"],
    endpoint="delete_report",
)