"""Authentication / authorisation middleware.

Provides:
- `login_required`  : any authenticated, non-suspended user
- `role_required`   : restrict a view to specific roles
- `get_current_user`: the User for the active JWT (cached per request)
- JWT error handlers that return JSON for /api/* and redirect for pages
"""

from functools import wraps

from flask import flash, g, jsonify, redirect, request, url_for
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from extensions import db, jwt
from models.user import User

_USER_CACHE_ATTR = "_healthai_current_user_cache"
_MISSING = object()


def get_current_user() -> User | None:
    """Return the user for the current JWT, or None. Cached per request."""
    cached = getattr(request, _USER_CACHE_ATTR, _MISSING)
    if cached is not _MISSING:
        return cached

    user = None
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity is not None:
            user = db.session.get(User, int(identity))
    except Exception:
        user = None
    # Cache on the request object (not `g`): `g` is scoped to the app context,
    # and Flask reuses an enclosing app context across requests (e.g. inside
    # `with app.app_context(): client.get(...)`), which would leak the previous
    # request's user into the next one.
    setattr(request, _USER_CACHE_ATTR, user)
    return user


def _wants_json() -> bool:
    return request.path.startswith("/api/")


def _unauthorized(message: str):
    if _wants_json():
        return jsonify({"success": False, "error": message}), 401
    flash("Please sign in to continue.", "warning")
    return redirect(url_for("auth.login_page", next=request.path))


def login_required(fn):
    """Require a valid JWT belonging to an active, non-suspended user."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return _unauthorized("Authentication required.")
        user = get_current_user()
        if user is None or not user.can_login:
            return _unauthorized("Your session is no longer valid.")
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles: str):
    """Require the authenticated user to hold one of the given roles."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return _unauthorized("Authentication required.")
            user = get_current_user()
            if user is None or not user.can_login:
                return _unauthorized("Your session is no longer valid.")
            if not user.has_role(*roles):
                if _wants_json():
                    return (
                        jsonify({"success": False, "error": "Permission denied."}),
                        403,
                    )
                flash("You don't have permission to access that page.", "danger")
                return redirect(url_for("main.dashboard_redirect"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def register_jwt_handlers(app) -> None:
    """Attach JWT failure handlers (expired / missing / invalid tokens)."""

    @jwt.expired_token_loader
    def handle_expired(_header, _payload):
        if _wants_json():
            return jsonify({"success": False, "error": "Token has expired."}), 401
        flash("Your session expired. Please sign in again.", "warning")
        return redirect(url_for("auth.login_page"))

    @jwt.unauthorized_loader
    def handle_missing(reason):
        if _wants_json():
            return jsonify({"success": False, "error": reason}), 401
        flash("Please sign in to continue.", "warning")
        return redirect(url_for("auth.login_page"))

    @jwt.invalid_token_loader
    def handle_invalid(reason):
        if _wants_json():
            return jsonify({"success": False, "error": "Invalid token."}), 401
        flash("Your session is invalid. Please sign in again.", "warning")
        return redirect(url_for("auth.login_page"))
