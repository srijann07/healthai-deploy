"""URL wiring for the admin module. Logic lives in controllers/admin_controller."""

from flask import Blueprint

from controllers import admin_controller

admin_bp = Blueprint("admin", __name__)

# --- Pages -----------------------------------------------------------------
admin_bp.add_url_rule(
    "/admin/dashboard",
    view_func=admin_controller.dashboard,
    methods=["GET"],
    endpoint="dashboard",
)
admin_bp.add_url_rule(
    "/admin/users",
    view_func=admin_controller.users_page,
    methods=["GET"],
    endpoint="users_page",
)
admin_bp.add_url_rule(
    "/admin/patients",
    view_func=admin_controller.patients_page,
    methods=["GET"],
    endpoint="patients_page",
)
admin_bp.add_url_rule(
    "/admin/patients/<int:patient_id>",
    view_func=admin_controller.patient_detail_page,
    methods=["GET"],
    endpoint="patient_detail_page",
)
admin_bp.add_url_rule(
    "/admin/doctors",
    view_func=admin_controller.doctors_page,
    methods=["GET"],
    endpoint="doctors_page",
)
admin_bp.add_url_rule(
    "/admin/predictions",
    view_func=admin_controller.predictions_page,
    methods=["GET"],
    endpoint="predictions_page",
)
admin_bp.add_url_rule(
    "/admin/appointments",
    view_func=admin_controller.appointments_page,
    methods=["GET", "POST"],
    endpoint="appointments_page",
)
admin_bp.add_url_rule(
    "/admin/reports",
    view_func=admin_controller.reports_page,
    methods=["GET"],
    endpoint="reports_page",
)
admin_bp.add_url_rule(
    "/admin/audit",
    view_func=admin_controller.audit_page,
    methods=["GET"],
    endpoint="audit_page",
)
admin_bp.add_url_rule(
    "/admin/announce",
    view_func=admin_controller.announce_page,
    methods=["GET", "POST"],
    endpoint="announce_page",
)

# --- Actions ---------------------------------------------------------------
admin_bp.add_url_rule(
    "/admin/users/<int:user_id>/toggle",
    view_func=admin_controller.user_toggle,
    methods=["POST"],
    endpoint="user_toggle",
)
admin_bp.add_url_rule(
    "/admin/users/<int:user_id>/role",
    view_func=admin_controller.user_change_role,
    methods=["POST"],
    endpoint="user_change_role",
)
admin_bp.add_url_rule(
    "/admin/users/<int:user_id>/delete",
    view_func=admin_controller.user_delete,
    methods=["POST"],
    endpoint="user_delete",
)
admin_bp.add_url_rule(
    "/admin/patients/<int:patient_id>/doctor",
    view_func=admin_controller.patient_assign_doctor,
    methods=["POST"],
    endpoint="patient_assign_doctor",
)
admin_bp.add_url_rule(
    "/admin/doctors/create",
    view_func=admin_controller.doctor_create,
    methods=["POST"],
    endpoint="doctor_create",
)
admin_bp.add_url_rule(
    "/admin/doctors/<int:doctor_id>/toggle-availability",
    view_func=admin_controller.doctor_toggle_availability,
    methods=["POST"],
    endpoint="doctor_toggle_availability",
)
admin_bp.add_url_rule(
    "/admin/doctors/<int:doctor_id>/delete",
    view_func=admin_controller.doctor_delete,
    methods=["POST"],
    endpoint="doctor_delete",
)
admin_bp.add_url_rule(
    "/admin/reports/<int:report_id>/download",
    view_func=admin_controller.report_download,
    methods=["GET"],
    endpoint="report_download",
)
admin_bp.add_url_rule(
    "/admin/reports/<int:report_id>/delete",
    view_func=admin_controller.report_delete,
    methods=["POST"],
    endpoint="report_delete",
)