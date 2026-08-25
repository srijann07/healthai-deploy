"""Business logic for registration, login and password recovery."""

from datetime import datetime, timezone

from flask import current_app

from extensions import db
from models.patient import Patient
from models.role import Role
from models.user import User
from services import token_service, validation_service as v
from services.audit_service import log_action
from services.notification_service import notify
from models.notification import Notification


class AuthError(Exception):
    """Raised for authentication failures. Message is user-safe."""


def register_patient(data: dict) -> User:
    """Create a patient account plus its linked profile row."""
    email = v.validate_email_address(data.get("email"))
    first_name = v.validate_name(data.get("first_name"), "First name")
    last_name = v.validate_name(data.get("last_name"), "Last name")
    phone = v.validate_phone(data.get("phone", ""))
    password = v.validate_password_strength(data.get("password"))

    if data.get("password") != data.get("confirm_password"):
        raise v.ValidationError("Passwords do not match.")
    if User.query.filter_by(email=email).first():
        raise v.ValidationError("An account with this email already exists.")

    gender = data.get("gender") or ""
    if gender:
        gender = v.validate_choice(gender, "Gender", ("male", "female", "other"))

    role = Role.get_by_name(Role.PATIENT)
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone or None,
        role=role,
    )
    user.set_password(password)
    user.patient_profile = Patient(gender=gender or None)

    db.session.add(user)
    db.session.commit()

    from services.doctor_service import assign_doctor_to_patient

    assign_doctor_to_patient(user.patient_profile)

    log_action("register", user_id=user.id, entity="user", entity_id=user.id)
    notify(
        user.id,
        "Welcome to HealthAI",
        "Your account was created successfully. Complete your profile to get "
        "more accurate predictions.",
        Notification.CATEGORY_PROFILE,
    )
    return user


def authenticate(email: str, password: str) -> User:
    """Validate credentials and return the user, or raise AuthError."""
    email = (email or "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password or ""):
        log_action("login_failed", details=f"email={email[:100]}")
        raise AuthError("Invalid email or password.")
    if user.is_suspended:
        log_action("login_blocked_suspended", user_id=user.id)
        raise AuthError("This account has been suspended. Contact support.")
    if not user.is_active:
        log_action("login_blocked_inactive", user_id=user.id)
        raise AuthError("This account has been deactivated.")

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    log_action("login", user_id=user.id)
    return user


def authenticate_by_phone_otp(phone: str, otp_code: str) -> User:
    """Verify phone OTP and authenticate the user associated with that Indian phone number."""
    from services import otp_service
    from services.otp_service import OtpError

    normalized_phone = v.validate_indian_phone(phone, required=True)

    try:
        otp_service.verify_otp(normalized_phone, otp_code, purpose="login")
    except OtpError as err:
        log_action("login_otp_failed", details=f"phone={normalized_phone[:15]}")
        raise AuthError(str(err))

    # Match normalized '+91XXXXXXXXXX' or 10-digit formats in database
    digits_10 = normalized_phone[-10:]
    user = User.query.filter(
        (User.phone == normalized_phone)
        | (User.phone == digits_10)
        | (User.phone == f"0{digits_10}")
        | (User.phone == f"91{digits_10}")
    ).first()

    if not user:
        # Seamlessly auto-register a new Patient account for any new Indian phone number
        import secrets

        role = Role.get_by_name(Role.PATIENT)
        temp_email = f"patient_{digits_10}@healthai.local"
        if User.query.filter_by(email=temp_email).first():
            temp_email = f"patient_{digits_10}_{secrets.token_hex(2)}@healthai.local"

        user = User(
            email=temp_email,
            first_name="Patient",
            last_name=digits_10[-4:],
            phone=normalized_phone,
            role=role,
        )
        user.set_password(f"HealthAI@{secrets.token_hex(4)}")
        user.patient_profile = Patient()

        db.session.add(user)
        db.session.commit()

        from services.doctor_service import assign_doctor_to_patient

        assign_doctor_to_patient(user.patient_profile)

        log_action(
            "register_via_phone_otp",
            user_id=user.id,
            entity="user",
            entity_id=user.id,
            details=f"phone={normalized_phone}",
        )
        notify(
            user.id,
            "Welcome to HealthAI",
            "Your account was created via your mobile number. You can update your name and details anytime in your profile.",
            Notification.CATEGORY_PROFILE,
        )
    else:
        if user.is_suspended:
            log_action("login_blocked_suspended", user_id=user.id)
            raise AuthError("This account has been suspended. Contact support.")
        if not user.is_active:
            log_action("login_blocked_inactive", user_id=user.id)
            raise AuthError("This account has been deactivated.")

        if user.phone != normalized_phone:
            user.phone = normalized_phone

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    log_action("login_otp", user_id=user.id)
    return user


def initiate_password_reset(email: str) -> str | None:
    """Generate a reset link for the account, if it exists.

    Returns the link (in production this would be emailed; in development
    it is logged to the server console). Always behaves identically to the
    caller whether or not the account exists, to avoid user enumeration.
    """
    email = (email or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or not user.can_login:
        return None

    token = token_service.generate_reset_token(user.id)
    base_url = current_app.config["APP_BASE_URL"].rstrip("/")
    link = f"{base_url}/reset-password/{token}"

    # No SMTP configured in development: surface the link in the server log.
    current_app.logger.info("Password reset link for %s: %s", email, link)
    log_action("password_reset_requested", user_id=user.id)
    return link


def reset_password(token: str, password: str, confirm_password: str) -> User:
    """Set a new password from a valid reset token."""
    user_id = token_service.verify_reset_token(token)
    if not user_id:
        raise AuthError("This reset link is invalid or has expired.")

    v.validate_password_strength(password)
    if password != confirm_password:
        raise v.ValidationError("Passwords do not match.")

    user = db.session.get(User, user_id)
    if not user or not user.can_login:
        raise AuthError("This reset link is invalid or has expired.")

    user.set_password(password)
    db.session.commit()
    log_action("password_reset_completed", user_id=user.id)
    notify(
        user.id,
        "Password changed",
        "Your account password was changed. If this wasn't you, contact support "
        "immediately.",
        Notification.CATEGORY_PROFILE,
    )
    return user
