"""Centralised Flask extension instances.

Keeping extensions here (instead of in app.py) avoids circular imports:
models and services import from `extensions`, never from `app`.
"""

from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
