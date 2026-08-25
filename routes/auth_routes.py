"""URL wiring for authentication. Logic lives in controllers/auth_controller."""

from flask import Blueprint

from controllers import auth_controller

auth_bp = Blueprint("auth", __name__)
auth_api_bp = Blueprint("auth_api", __name__, url_prefix="/api")

# --- Web pages ------------------------------------------------------------
auth_bp.add_url_rule(
    "/login", view_func=auth_controller.login_page, methods=["GET", "POST"],
    endpoint="login_page",
)
auth_bp.add_url_rule(
    "/send-otp", view_func=auth_controller.send_otp, methods=["POST"],
    endpoint="send_otp",
)
auth_bp.add_url_rule(
    "/login-otp", view_func=auth_controller.login_otp_page, methods=["POST"],
    endpoint="login_otp",
)
auth_bp.add_url_rule(
    "/register", view_func=auth_controller.register_page, methods=["GET", "POST"],
    endpoint="register_page",
)
auth_bp.add_url_rule(
    "/forgot-password",
    view_func=auth_controller.forgot_password_page,
    methods=["GET", "POST"],
    endpoint="forgot_password_page",
)
auth_bp.add_url_rule(
    "/reset-password/<token>",
    view_func=auth_controller.reset_password_page,
    methods=["GET", "POST"],
    endpoint="reset_password_page",
)
auth_bp.add_url_rule("/logout", view_func=auth_controller.logout, endpoint="logout")

# --- JSON API -------------------------------------------------------------
auth_api_bp.add_url_rule(
    "/register", view_func=auth_controller.api_register, methods=["POST"],
    endpoint="register",
)
auth_api_bp.add_url_rule(
    "/login", view_func=auth_controller.api_login, methods=["POST"],
    endpoint="login",
)
auth_api_bp.add_url_rule(
    "/auth/send-otp", view_func=auth_controller.api_send_otp, methods=["POST"],
    endpoint="api_send_otp",
)
auth_api_bp.add_url_rule(
    "/auth/login-otp", view_func=auth_controller.api_verify_otp, methods=["POST"],
    endpoint="api_login_otp",
)
auth_api_bp.add_url_rule(
    "/auth/verify-otp", view_func=auth_controller.api_verify_otp, methods=["POST"],
    endpoint="api_verify_otp",
)
