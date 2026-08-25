"""Request handling for authentication (web pages + JSON API)."""

from flask import (
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from models.role import Role
from models.user import User
from services import auth_service, otp_service
from services.auth_service import AuthError
from services.otp_service import OtpError
from services.validation_service import ValidationError

DASHBOARD_ENDPOINTS = {
    Role.PATIENT: "main.patient_dashboard",
    Role.DOCTOR: "main.doctor_dashboard",
    Role.ADMIN: "main.admin_dashboard",
}


def _issue_tokens(user: User):
    """Create JWT access + refresh tokens with the user's role as a claim."""
    claims = {"role": user.role_name}
    access = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh = create_refresh_token(identity=str(user.id), additional_claims=claims)
    return access, refresh


def _safe_next_url(target: str | None) -> str | None:
    """Only allow same-site relative redirects (open-redirect protection)."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


# ----------------------------------------------------------------------
# Web pages
# ----------------------------------------------------------------------

def login_page():
    if request.method == "GET":
        return render_template("auth/login.html")

    try:
        user = auth_service.authenticate(
            request.form.get("email"), request.form.get("password")
        )
    except AuthError as exc:
        flash(str(exc), "danger")
        return render_template("auth/login.html", email=request.form.get("email", "")), 401

    endpoint = DASHBOARD_ENDPOINTS.get(user.role_name, "main.index")
    target = _safe_next_url(request.args.get("next")) or url_for(endpoint)
    response = make_response(redirect(target))
    access, refresh = _issue_tokens(user)
    set_access_cookies(response, access)
    set_refresh_cookies(response, refresh)
    flash(f"Welcome back, {user.first_name}!", "success")
    return response


def register_page():
    if request.method == "GET":
        return render_template("auth/register.html")

    try:
        auth_service.register_patient(request.form.to_dict())
    except ValidationError as exc:
        flash(str(exc), "danger")
        return render_template("auth/register.html", form=request.form), 400

    flash("Account created successfully. Please sign in.", "success")
    return redirect(url_for("auth.login_page"))


def forgot_password_page():
    if request.method == "GET":
        return render_template("auth/forgot_password.html")

    auth_service.initiate_password_reset(request.form.get("email"))
    # Same message whether or not the account exists (no user enumeration).
    flash(
        "If an account exists for that email, a password reset link has been "
        "sent. (Development mode: the link is printed in the server console.)",
        "info",
    )
    return redirect(url_for("auth.login_page"))


def reset_password_page(token: str):
    if request.method == "GET":
        return render_template("auth/reset_password.html", token=token)

    try:
        auth_service.reset_password(
            token,
            request.form.get("password", ""),
            request.form.get("confirm_password", ""),
        )
    except (AuthError, ValidationError) as exc:
        flash(str(exc), "danger")
        return render_template("auth/reset_password.html", token=token), 400

    flash("Password updated. Please sign in with your new password.", "success")
    return redirect(url_for("auth.login_page"))


def logout():
    response = make_response(redirect(url_for("auth.login_page")))
    unset_jwt_cookies(response)
    flash("You have been signed out.", "info")
    return response


def send_otp():
    """Dispatch OTP for Indian mobile number via AJAX or form POST."""
    req_json = request.get_json(silent=True) or {}
    phone = req_json.get("phone") or request.form.get("phone")
    purpose = req_json.get("purpose") or request.form.get("purpose") or "login"

    try:
        res = otp_service.generate_and_send_otp(phone, purpose=purpose)
        return jsonify(
            {
                "success": True,
                "message": f"Verification code sent to {res['phone']}. Please check your SMS.",
                "phone": res["phone"],
                "dev_otp": res.get("dev_otp"),
                "expires_in_seconds": res["expires_in_seconds"],
            }
        )
    except (ValidationError, OtpError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


def login_otp_page():
    """Handle form submission for Indian mobile OTP login."""
    phone = request.form.get("phone", "")
    otp_code = request.form.get("otp", "")

    try:
        user = auth_service.authenticate_by_phone_otp(phone, otp_code)
    except (AuthError, ValidationError, OtpError) as exc:
        flash(str(exc), "danger")
        return (
            render_template("auth/login.html", active_tab="otp", phone=phone),
            401,
        )

    endpoint = DASHBOARD_ENDPOINTS.get(user.role_name, "main.index")
    target = _safe_next_url(request.args.get("next")) or url_for(endpoint)
    response = make_response(redirect(target))
    access, refresh = _issue_tokens(user)
    set_access_cookies(response, access)
    set_refresh_cookies(response, refresh)
    flash(f"Welcome back, {user.first_name}!", "success")
    return response


# ----------------------------------------------------------------------
# JSON API
# ----------------------------------------------------------------------

def api_register():
    data = request.get_json(silent=True) or {}
    try:
        user = auth_service.register_patient(data)
    except ValidationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return (
        jsonify(
            {
                "success": True,
                "message": "Account created successfully.",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "phone": user.phone,
                    "full_name": user.full_name,
                    "role": user.role_name,
                },
            }
        ),
        201,
    )


def api_login():
    data = request.get_json(silent=True) or {}
    try:
        user = auth_service.authenticate(data.get("email"), data.get("password"))
    except AuthError as exc:
        return jsonify({"success": False, "error": str(exc)}), 401

    access, refresh = _issue_tokens(user)
    return jsonify(
        {
            "success": True,
            "access_token": access,
            "refresh_token": refresh,
            "user": {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "full_name": user.full_name,
                "role": user.role_name,
            },
        }
    )


def api_send_otp():
    """API endpoint to request OTP for an Indian phone number."""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    purpose = data.get("purpose", "login")
    try:
        res = otp_service.generate_and_send_otp(phone, purpose=purpose)
        return jsonify(
            {
                "success": True,
                "message": f"OTP sent to {res['phone']}",
                "phone": res["phone"],
                "dev_otp": res.get("dev_otp"),
                "expires_in_seconds": res["expires_in_seconds"],
            }
        )
    except (ValidationError, OtpError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


def api_verify_otp():
    """API endpoint to login using Indian mobile OTP."""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    otp_code = data.get("otp")
    try:
        user = auth_service.authenticate_by_phone_otp(phone, otp_code)
    except (AuthError, ValidationError, OtpError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 401

    access, refresh = _issue_tokens(user)
    return jsonify(
        {
            "success": True,
            "access_token": access,
            "refresh_token": refresh,
            "user": {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "full_name": user.full_name,
                "role": user.role_name,
            },
        }
    )
