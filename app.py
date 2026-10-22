"""HealthAI application factory and entry point.

Run locally:
    python app.py            (or: flask --app app run)
Seed initial data first:
    python seed.py
"""

import os

from flask import render_template, request

from config import BASE_DIR, get_config
from extensions import db, jwt
from middlewares.auth_middleware import get_current_user, register_jwt_handlers
from routes import register_routes


def create_app(env_name: str | None = None):
    from flask import Flask

    app = Flask(__name__)
    cfg = get_config(env_name)
    app.config.from_object(cfg)

    # Resilient Database Connection: Verify remote database before binding
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri and not db_uri.startswith("sqlite"):
        try:
            import sqlalchemy as sa
            connect_args = {}
            if "postgres" in db_uri:
                connect_args["connect_timeout"] = 3
            test_engine = sa.create_engine(db_uri, connect_args=connect_args)
            with test_engine.connect() as conn:
                pass
            test_engine.dispose()
        except Exception as exc:
            app.logger.warning("Remote database connection failed (%s). Falling back to SQLite.", exc)
            app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "healthai_dev.db")
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    # --- Extensions ---------------------------------------------------
    db.init_app(app)
    jwt.init_app(app)
    register_jwt_handlers(app)

    # --- Blueprints ---------------------------------------------------
    register_routes(app)

    # --- Ensure runtime folders exist --------------------------------
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["ML_MODEL_DIR"], exist_ok=True)

    # --- Template context ---------------------------------------------
    @app.context_processor
    def inject_globals():
        user = get_current_user()
        return {
            "current_user": user,
            "app_name": app.config["APP_NAME"],
            # CSRF token for HTML form posts to JWT-protected endpoints.
            "csrf_token": request.cookies.get("csrf_access_token", ""),
        }

    # --- Error pages ---------------------------------------------------
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # --- Security headers ----------------------------------------------
    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    # --- CLI helpers ----------------------------------------------------
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        db.create_all()
        print("Database tables created.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
