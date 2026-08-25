"""Seed demo accounts so visitors can explore both patient and doctor views.

Creates one patient and one doctor (with profiles) if they do not exist.
Idempotent: safe to run multiple times.

Usage:
    python seed_demo_users.py
"""

from datetime import date

from app import create_app
from extensions import db
from models.doctor import Doctor
from models.patient import Patient
from models.role import Role
from models.user import User


def get_or_create(email, first_name, last_name, password, role_name, phone=None):
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
    print("Seeding demo accounts...")
    db.create_all()
    Role.seed_defaults()

    patient_user = get_or_create(
        "demo.patient@healthai.local",
        "Aarav",
        "Patel",
        "Patient@12345",
        Role.PATIENT,
        phone="+919876543210",
    )
    if not patient_user.patient_profile:
        patient_user.patient_profile = Patient(
            date_of_birth=date(1992, 5, 14),
            gender="male",
            blood_group="B+",
            height_cm=172.0,
            weight_kg=78.0,
            address="12 Lakeview Road",
            emergency_contact="+91 90000 12345",
        )
        db.session.commit()
        print(f"  + created patient profile for {patient_user.email}")

    doctor_user = get_or_create(
        "demo.doctor@healthai.local",
        "Kabir",
        "Rao",
        "Doctor@12345",
        Role.DOCTOR,
        phone="+919876543211",
    )
    if not doctor_user.doctor_profile:
        doctor_user.doctor_profile = Doctor(
            specialization="General Physician",
            license_number="MCI-2019-55234",
            years_experience=7,
            hospital="HealthAI Partner Clinic",
            bio="Preventive medicine and lifestyle counselling.",
        )
        db.session.commit()
        print(f"  + created doctor profile for {doctor_user.email}")

    if patient_user.patient_profile and doctor_user.doctor_profile:
        if patient_user.patient_profile.assigned_doctor_id is None:
            patient_user.patient_profile.assigned_doctor = doctor_user.doctor_profile
            db.session.commit()
            print(f"  + assigned {doctor_user.email} to {patient_user.email}")

    print("Done.")


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        seed()
