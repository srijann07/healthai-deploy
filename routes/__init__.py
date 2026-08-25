"""Blueprint registry. `register_routes(app)` wires every blueprint."""

from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp, auth_api_bp
from routes.doctor_routes import doctor_bp
from routes.main_routes import main_bp
from routes.patient_routes import patient_api_bp, patient_bp


def register_routes(app) -> None:
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(auth_api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(patient_api_bp)
    app.register_blueprint(doctor_bp)
