"""Reusable input validation helpers.

All user input passes through these before touching the database, which
(together with SQLAlchemy's parameterised queries and Jinja2 autoescaping)
covers SQL-injection and XSS protection.
"""

import re
from datetime import date, datetime

from email_validator import EmailNotValidError, validate_email

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{0,59}$")
PHONE_RE = re.compile(r"^\+?[0-9 \-]{7,19}$")
PASSWORD_MIN_LENGTH = 8

MAX_AGE_YEARS = 120
GENDERS = ("male", "female", "other")
BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
SMOKING_STATUSES = ("never", "former", "occasional", "regular")
ALCOHOL_LEVELS = ("none", "occasional", "regular")
EXERCISE_LEVELS = ("daily", "several_per_week", "few_per_week", "rarely", "never")


class ValidationError(Exception):
    """Raised when user input fails validation. Message is user-safe."""


def clean_str(value, max_length: int = 255) -> str:
    """Strip whitespace and enforce a max length on free-text input."""
    value = (value or "").strip()
    if len(value) > max_length:
        raise ValidationError(f"Value is too long (max {max_length} characters).")
    return value


def require(value, field_name: str):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required.")
    return value


EMAIL_SIMPLE_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_address(email: str) -> str:
    """Validate and normalise an email address."""
    email = (email or "").strip().lower()
    if not email:
        raise ValidationError("Please enter a valid email address.")
    try:
        result = validate_email(email, check_deliverability=False)
        return result.normalized.lower()
    except EmailNotValidError:
        if EMAIL_SIMPLE_RE.match(email):
            return email
        raise ValidationError("Please enter a valid email address.")


def validate_name(name: str, field_name: str) -> str:
    name = clean_str(name, 60)
    if not NAME_RE.match(name):
        raise ValidationError(
            f"{field_name} may only contain letters, spaces, hyphens and apostrophes."
        )
    return name


INDIAN_PHONE_DIGITS_RE = re.compile(r"^[6-9]\d{9}$")


def validate_indian_phone(phone: str, required: bool = True) -> str:
    """Validate and normalize an Indian mobile phone number.

    Accepts:
      - 10 digits starting with 6, 7, 8, 9 (e.g. "9876543210")
      - prefixed with +91 (e.g. "+91 98765 43210", "+919876543210")
      - prefixed with 91 (e.g. "919876543210")
      - prefixed with 0 (e.g. "09876543210")

    Returns:
      Normalized E.164 format: "+91XXXXXXXXXX" (e.g. "+919876543210")
    """
    raw = (phone or "").strip()
    if not raw:
        if required:
            raise ValidationError("Please enter your 10-digit Indian mobile number.")
        return ""

    # Strip spaces, hyphens, parentheses, dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", raw)
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    if not INDIAN_PHONE_DIGITS_RE.match(cleaned):
        raise ValidationError(
            "Please enter a valid 10-digit Indian mobile number (e.g. 9876543210 or +919876543210)."
        )
    return f"+91{cleaned}"


def validate_phone(phone: str, required: bool = False) -> str:
    """Validate phone number ensuring it follows Indian mobile number rules."""
    raw = clean_str(phone, 25)
    if not raw:
        if required:
            raise ValidationError("Phone number is required.")
        return ""
    return validate_indian_phone(raw, required=required)


def validate_password_strength(password: str) -> str:
    password = password or ""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain both letters and numbers.")
    return password


def validate_choice(value: str, field_name: str, choices: tuple | list) -> str:
    value = clean_str(value, 50)
    if value not in choices:
        raise ValidationError(f"Invalid value for {field_name}.")
    return value


def validate_number(
    value, field_name: str, minimum: float, maximum: float, integer: bool = False
):
    """Parse and range-check a numeric field."""
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a number.")
    if number < minimum or number > maximum:
        raise ValidationError(
            f"{field_name} must be between {minimum:g} and {maximum:g}."
        )
    return number


def validate_optional_number(value, field_name: str, minimum: float, maximum: float):
    """Validate a numeric field that may be left blank. Blank -> None."""
    value = (value or "").strip()
    if not value:
        return None
    return validate_number(value, field_name, minimum, maximum)


def validate_date(value, field_name: str, max_age: int = MAX_AGE_YEARS):
    """Parse a YYYY-MM-DD date; reject future dates and unreasonable ages."""
    value = (value or "").strip()
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{field_name} must be a valid date (YYYY-MM-DD).")
    today = date.today()
    if parsed > today:
        raise ValidationError(f"{field_name} cannot be in the future.")
    age = today.year - parsed.year - (
        (today.month, today.day) < (parsed.month, parsed.day)
    )
    if age > max_age:
        raise ValidationError(f"{field_name} implies an age over {max_age} years.")
    return parsed


def validate_optional_text(value, field_name: str, max_length: int = 2000) -> str:
    """Free-text input that may be blank. Blank -> empty string."""
    value = (value or "").strip()
    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} is too long (max {max_length} characters)."
        )
    return value
