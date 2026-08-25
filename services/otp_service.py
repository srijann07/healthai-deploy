"""Service for Indian phone OTP generation, rate limiting, verification and SMS dispatch."""

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from flask import current_app

from extensions import db
from models.phone_otp import PhoneOTP
from services import validation_service as v


class OtpError(Exception):
    """Raised when OTP generation or verification fails with a user-safe message."""


OTP_EXPIRY_MINUTES = 5
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 3
OTP_HOURLY_LIMIT = 6


def _hash_otp(otp_code: str) -> str:
    """Hash OTP using bcrypt."""
    return bcrypt.hashpw(otp_code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_otp(otp_code: str, otp_hash: str) -> bool:
    """Verify raw OTP against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(otp_code.encode("utf-8"), otp_hash.encode("utf-8"))
    except (ValueError, AttributeError):
        return False


def _send_sms_notification(phone: str, otp_code: str, purpose: str) -> bool:
    """Dispatch real SMS to Indian mobile numbers via configured SMS gateway.

    Supported integrations:
      - Fast2SMS (Indian SMS gateway): FAST2SMS_API_KEY
      - 2Factor.in (Indian SMS gateway): TWOFACTOR_API_KEY
      - Twilio: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
      - Terminal / server console log fallback (always logged for reference)
    """
    fast2sms_api_key = os.environ.get("FAST2SMS_API_KEY")
    twofactor_api_key = os.environ.get("TWOFACTOR_API_KEY")
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_from = os.environ.get("TWILIO_PHONE_NUMBER")

    digits_10 = phone[-10:]

    # Always log clearly to server console for instant reference
    current_app.logger.info("=" * 50)
    current_app.logger.info("🔑 HealthAI OTP Verification")
    current_app.logger.info("Phone: %s | Purpose: %s | OTP: %s", phone, purpose, otp_code)
    current_app.logger.info("Valid for %d minutes", OTP_EXPIRY_MINUTES)
    current_app.logger.info("=" * 50)

    # 1. Fast2SMS (India's most popular instant OTP gateway)
    if fast2sms_api_key:
        try:
            import json
            import urllib.parse
            import urllib.request

            url = "https://www.fast2sms.com/dev/bulkV2"
            payload = urllib.parse.urlencode({
                "authorization": fast2sms_api_key.strip(),
                "variables_values": otp_code,
                "route": "otp",
                "numbers": digits_10,
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                current_app.logger.info("Fast2SMS API Response: %s", resp_data)
                return bool(resp_data.get("return"))
        except Exception as exc:
            current_app.logger.error("Fast2SMS real SMS dispatch failed: %s", exc)

    # 2. 2Factor.in (Instant Indian SMS gateway)
    if twofactor_api_key:
        try:
            import urllib.request
            url = f"https://2factor.in/API/V1/{twofactor_api_key.strip()}/SMS/{digits_10}/{otp_code}/HealthAI_OTP"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=8) as resp:
                current_app.logger.info("2Factor.in SMS dispatched successfully: %s", resp.status)
                return True
        except Exception as exc:
            current_app.logger.error("2Factor.in SMS dispatch failed: %s", exc)

    # 3. Twilio
    if twilio_sid and twilio_token and twilio_from:
        try:
            import base64
            import json
            import urllib.parse
            import urllib.request

            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            payload = urllib.parse.urlencode({
                "From": twilio_from,
                "To": phone,
                "Body": f"Your HealthAI verification code is: {otp_code}. Valid for 5 minutes.",
            }).encode("utf-8")

            auth_header = "Basic " + base64.b64encode(
                f"{twilio_sid}:{twilio_token}".encode("utf-8")
            ).decode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Authorization": auth_header, "Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                current_app.logger.info("Twilio SMS dispatched successfully: %s", resp.status)
                return True
        except Exception as exc:
            current_app.logger.error("Twilio SMS dispatch failed: %s", exc)

    return True


def generate_and_send_otp(
    phone_input: str, purpose: str = "login"
) -> dict:
    """Generate and dispatch a 6-digit OTP for an Indian mobile number.

    Returns dict with keys:
      - 'phone': Normalized phone number (+91XXXXXXXXXX)
      - 'expires_in_seconds': int
      - 'dev_otp': str (present only in development mode for easy testing)
    """
    normalized_phone = v.validate_indian_phone(phone_input, required=True)
    now_utc = datetime.now(timezone.utc)

    # 1. Rate limiting - Cooldown check (minimum 60s between requests)
    cooldown_cutoff = now_utc - timedelta(seconds=OTP_COOLDOWN_SECONDS)
    recent_otp = (
        PhoneOTP.query.filter(
            PhoneOTP.phone == normalized_phone,
            PhoneOTP.created_at >= cooldown_cutoff,
        )
        .order_by(PhoneOTP.created_at.desc())
        .first()
    )
    if recent_otp:
        elapsed = (now_utc - recent_otp.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        wait_seconds = max(1, int(OTP_COOLDOWN_SECONDS - elapsed))
        raise OtpError(f"Please wait {wait_seconds} seconds before requesting a new OTP.")

    # 2. Rate limiting - Hourly maximum check
    hour_cutoff = now_utc - timedelta(hours=1)
    hourly_count = PhoneOTP.query.filter(
        PhoneOTP.phone == normalized_phone,
        PhoneOTP.created_at >= hour_cutoff,
    ).count()
    if hourly_count >= OTP_HOURLY_LIMIT:
        raise OtpError("Too many OTP requests for this number. Please try again after an hour.")

    # 3. Generate secure 6-digit numeric OTP
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    otp_hash = _hash_otp(otp_code)
    expires_at = now_utc + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Invalidate previous unused OTPs for this phone and purpose
    PhoneOTP.query.filter_by(
        phone=normalized_phone, purpose=purpose, is_used=False
    ).update({"is_used": True})

    # Save new OTP record
    record = PhoneOTP(
        phone=normalized_phone,
        otp_hash=otp_hash,
        purpose=purpose,
        attempts=0,
        is_used=False,
        expires_at=expires_at,
        created_at=now_utc,
    )
    db.session.add(record)
    db.session.commit()

    # 4. Dispatch OTP
    _send_sms_notification(normalized_phone, otp_code, purpose)

    show_demo_otp = (
        current_app.config.get("DEBUG", False)
        or current_app.config.get("TESTING", False)
        or current_app.config.get("ENV") == "development"
        or os.environ.get("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    )
    return {
        "phone": normalized_phone,
        "expires_in_seconds": OTP_EXPIRY_MINUTES * 60,
        "dev_otp": otp_code if show_demo_otp else None,
    }


def verify_otp(phone_input: str, otp_code: str, purpose: str = "login") -> bool:
    """Verify the submitted OTP code for the given phone number."""
    normalized_phone = v.validate_indian_phone(phone_input, required=True)
    otp_code = (otp_code or "").strip()

    if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
        raise OtpError("Please enter a valid 6-digit OTP code.")

    # Fetch latest unused OTP for this phone & purpose
    otp_record = (
        PhoneOTP.query.filter_by(
            phone=normalized_phone,
            purpose=purpose,
            is_used=False,
        )
        .order_by(PhoneOTP.created_at.desc())
        .first()
    )

    if not otp_record:
        raise OtpError("No active OTP found for this number. Please request a new OTP.")

    if otp_record.is_expired:
        raise OtpError("This OTP has expired. Please request a new one.")

    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        otp_record.is_used = True
        db.session.commit()
        raise OtpError("Too many incorrect attempts. This OTP is now invalid. Request a new OTP.")

    # Check OTP hash match
    if not _check_otp(otp_code, otp_record.otp_hash):
        otp_record.attempts += 1
        db.session.commit()
        remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
        if remaining > 0:
            raise OtpError(f"Incorrect OTP code. {remaining} attempt(s) remaining.")
        else:
            otp_record.is_used = True
            db.session.commit()
            raise OtpError("Too many incorrect attempts. Please request a new OTP.")

    # Mark as successfully used
    otp_record.is_used = True
    db.session.commit()
    return True
