"""Seed the database with roles, an admin account and a demo doctor.

Usage:
    python seed.py
Idempotent: safe to run multiple times.
"""

import os

from app import create_app
from extensions import db
from models.doctor import Doctor
from models.role import Role
from models.user import User


def get_or_create_user(email, first_name, last_name, password, role_name, phone=None) -> User:
    user = User.query.filter_by(email=email).first()
    if user:
        if phone and not user.phone:
            user.phone = phone
            db.session.commit()
        print(f"  = {email} already exists, skipping")
        return user
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role=Role.get_by_name(role_name),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"  + created {role_name}: {email} / {password} (Phone: {phone})")
    return user


def seed():
    print("Creating tables...")
    db.create_all()

    print("Seeding roles...")
    Role.seed_defaults()

    print("Seeding accounts...")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@healthai.local")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@12345")
    get_or_create_user(admin_email, "System", "Administrator", admin_password, Role.ADMIN, phone="+919999999999")

    doctor_user = get_or_create_user(
        "dr.sharma@healthai.local", "Ananya", "Sharma", "Doctor@12345", Role.DOCTOR, phone="+919876500001"
    )
    if not doctor_user.doctor_profile:
        doctor_user.doctor_profile = Doctor(
            specialization="General Physician",
            license_number="MCI-2020-48291",
            years_experience=8,
            hospital="HealthAI Partner Clinic",
            bio="General physician focused on preventive care and early risk detection.",
        )
        db.session.commit()
        print("  + created doctor profile for dr.sharma@healthai.local")

    demo_doctors = [
        {
            "email": "dr.mehta@healthai.local",
            "first_name": "Rohan",
            "last_name": "Mehta",
            "phone": "+919876500002",
            "specialization": "Cardiologist",
            "license_number": "MCI-2016-33251",
            "years_experience": 12,
            "hospital": "HealthAI Partner Clinic",
            "bio": "Cardiologist specialising in hypertension and heart-disease risk screening.",
        },
        {
            "email": "dr.iyer@healthai.local",
            "first_name": "Priya",
            "last_name": "Iyer",
            "phone": "+919876500003",
            "specialization": "Endocrinologist",
            "license_number": "MCI-2018-90124",
            "years_experience": 10,
            "hospital": "HealthAI Partner Clinic",
            "bio": "Endocrinologist focused on diabetes detection and metabolic health.",
        },
    ]
    for details in demo_doctors:
        demo_user = get_or_create_user(
            details["email"],
            details["first_name"],
            details["last_name"],
            "Doctor@12345",
            Role.DOCTOR,
            phone=details["phone"],
        )
        if not demo_user.doctor_profile:
            demo_user.doctor_profile = Doctor(
                specialization=details["specialization"],
                license_number=details["license_number"],
                years_experience=details["years_experience"],
                hospital=details["hospital"],
                bio=details["bio"],
            )
            db.session.commit()
            print(f"  + created doctor profile for {details['email']}")

    print("Done.")


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        seed()
