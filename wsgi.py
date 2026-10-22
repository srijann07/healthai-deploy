import os

from app import create_app
from extensions import db
from models.role import Role

# Gunicorn / WSGI entry point
application = create_app()

# Auto-initialize database tables and seed default roles on startup
with application.app_context():
    try:
        db.create_all()
        Role.seed_defaults()
        # Seed default accounts if admin does not exist
        from models.user import User
        if not User.query.filter_by(email="admin@healthai.local").first():
            import seed
            seed.seed()
    except Exception as exc:
        application.logger.warning("Startup DB initialization skipped: %s", exc)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    application.run(host="0.0.0.0", port=port)
