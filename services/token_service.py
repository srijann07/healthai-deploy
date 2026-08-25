"""Time-limited signed tokens for password reset links."""

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = "healthai-password-reset"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_SALT)


def generate_reset_token(user_id: int) -> str:
    return _serializer().dumps({"user_id": user_id})


def verify_reset_token(token: str) -> int | None:
    """Return the user id if the token is valid and unexpired, else None."""
    max_age = current_app.config["PASSWORD_RESET_TOKEN_MAX_AGE"]
    try:
        data = _serializer().loads(token, max_age=max_age)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None
