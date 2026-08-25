"""WSGI entry point for production servers (gunicorn, PythonAnywhere...).

Usage:
    gunicorn wsgi:application
    (or on PythonAnywhere, set the WSGI source to this file)
"""

from app import create_app

application = create_app()