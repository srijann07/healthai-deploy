"""Business logic for medical report uploads, downloads, and deletion.

Supports multi-cloud storage backends (Local Disk, Firebase Cloud Storage, Supabase Storage).
Evaluators can view files directly in cloud storage consoles (Firebase/Supabase).
"""

import io
import os
import uuid
from typing import Tuple

from flask import current_app, redirect, send_file, send_from_directory

from extensions import db
from models.medical_report import MedicalReport
from models.patient import Patient
from services import validation_service as v
from services.audit_service import log_action


class ReportError(Exception):
    """Raised for report operations that must stop the request."""


# Magic bytes -> normalized type. `jpeg` maps to `jpg` for storage.
_MAGIC_BYTES = {
    "pdf": b"%PDF-",
    "jpg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
}
_MIME_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "png": "image/png",
}
_EXTENSION_ALIASES = {"jpeg": "jpg"}


def _detect_magic_type(content: bytes) -> str | None:
    """Match the file signature against known types, or return None."""
    for file_type, magic in _MAGIC_BYTES.items():
        if content.startswith(magic):
            return file_type
    return None


def _normalise_extension(extension: str) -> str:
    """Map an uploaded extension to its storage type (jpeg -> jpg)."""
    return _EXTENSION_ALIASES.get(extension, extension)


# --------------------------------------------------------------------------
# Cloud Storage Adapters (Firebase & Supabase)
# --------------------------------------------------------------------------

def _get_firebase_bucket():
    """Initialize and return the Firebase Cloud Storage bucket instance."""
    try:
        import firebase_admin
        from firebase_admin import credentials, storage

        if not firebase_admin._apps:
            cred_path = current_app.config.get("FIREBASE_CREDENTIALS_PATH")
            bucket_name = current_app.config.get("FIREBASE_STORAGE_BUCKET")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
            else:
                firebase_admin.initialize_app(options={"storageBucket": bucket_name})
        return storage.bucket()
    except Exception as exc:
        current_app.logger.warning("Firebase Storage initialization warning: %s", exc)
        return None


def _upload_to_firebase(stored_filename: str, file_bytes: bytes, mime_type: str) -> str | None:
    """Upload a file to Firebase Storage bucket and return its public/signed URL."""
    bucket = _get_firebase_bucket()
    if not bucket:
        return None
    try:
        blob = bucket.blob(f"medical_reports/{stored_filename}")
        blob.upload_from_string(file_bytes, content_type=mime_type)
        try:
            blob.make_public()
            return blob.public_url
        except Exception:
            return blob.generate_signed_url(version="v4", expiration=3600 * 24 * 7, method="GET")
    except Exception as exc:
        current_app.logger.error("Firebase upload failed: %s", exc)
        return None


def _delete_from_firebase(stored_filename: str) -> None:
    """Delete a file from Firebase Cloud Storage bucket."""
    bucket = _get_firebase_bucket()
    if not bucket:
        return
    try:
        blob = bucket.blob(f"medical_reports/{stored_filename}")
        if blob.exists():
            blob.delete()
    except Exception as exc:
        current_app.logger.warning("Firebase file delete failed: %s", exc)


def _upload_to_supabase(stored_filename: str, file_bytes: bytes, mime_type: str) -> str | None:
    """Upload a file to Supabase Storage bucket via REST API."""
    supabase_url = current_app.config.get("SUPABASE_URL")
    supabase_key = current_app.config.get("SUPABASE_KEY")
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "medical-reports")

    if not supabase_url or not supabase_key:
        return None

    try:
        import urllib.request
        base_url = supabase_url.rstrip("/")
        endpoint = f"{base_url}/storage/v1/object/{bucket}/{stored_filename}"
        req = urllib.request.Request(
            endpoint,
            data=file_bytes,
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "apikey": supabase_key,
                "Content-Type": mime_type,
                "x-upsert": "true",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                return f"{base_url}/storage/v1/object/public/{bucket}/{stored_filename}"
    except Exception as exc:
        current_app.logger.warning("Supabase storage upload error: %s", exc)
    return None


def _delete_from_supabase(stored_filename: str) -> None:
    """Delete a file from Supabase Storage bucket."""
    supabase_url = current_app.config.get("SUPABASE_URL")
    supabase_key = current_app.config.get("SUPABASE_KEY")
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "medical-reports")

    if not supabase_url or not supabase_key:
        return

    try:
        import json
        import urllib.request
        base_url = supabase_url.rstrip("/")
        endpoint = f"{base_url}/storage/v1/object/{bucket}"
        payload = json.dumps({"prefixes": [stored_filename]}).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "apikey": supabase_key,
                "Content-Type": "application/json",
            },
            method="DELETE",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        current_app.logger.warning("Supabase storage delete error: %s", exc)


# --------------------------------------------------------------------------
# Main Service Interface
# --------------------------------------------------------------------------

def save_report(patient: Patient, file_storage, description: str = "") -> MedicalReport:
    """Validate, persist and store one uploaded report file across configured storage."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise ReportError("Please choose a file to upload.")

    original_filename = os.path.basename(file_storage.filename.strip())
    if not original_filename:
        raise ReportError("Please choose a file to upload.")

    allowed = current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    extension = original_filename.rsplit(".", 1)[-1].lower()
    if extension not in allowed:
        raise ReportError("Only PDF, JPG and PNG files are allowed.")

    file_bytes = file_storage.read()
    if not file_bytes:
        raise ReportError("Uploaded file is empty.")

    detected = _detect_magic_type(file_bytes[:16])
    if detected != _normalise_extension(extension):
        raise ReportError(
            "The file contents do not match its extension. Only PDF, JPG and PNG files are allowed."
        )

    stored_filename = f"{uuid.uuid4().hex}.{detected}"
    mime_type = _MIME_TYPES.get(detected, "application/octet-stream")
    provider = current_app.config.get("STORAGE_PROVIDER", "local")
    cloud_url = None

    # Always save a local copy if local upload folder exists
    local_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)
    try:
        with open(local_path, "wb") as f:
            f.write(file_bytes)
    except Exception as exc:
        current_app.logger.warning("Local file write error: %s", exc)

    # Cloud Storage Uploads
    if provider == "firebase":
        cloud_url = _upload_to_firebase(stored_filename, file_bytes, mime_type)
        if not cloud_url:
            provider = "local"  # Fallback gracefully
    elif provider == "supabase":
        cloud_url = _upload_to_supabase(stored_filename, file_bytes, mime_type)
        if not cloud_url:
            provider = "local"

    report = MedicalReport(
        patient=patient,
        stored_filename=stored_filename,
        original_filename=original_filename[:255],
        file_type=detected,
        file_size=len(file_bytes),
        description=(
            v.validate_optional_text(description or "", "Description", max_length=255)
            or None
        ),
        storage_provider=provider,
        storage_url=cloud_url,
    )
    db.session.add(report)
    db.session.commit()

    log_action(
        "report_uploaded",
        user_id=patient.user_id,
        entity="medical_report",
        entity_id=report.id,
        details=f"{original_filename} (storage={provider})",
    )
    return report


def save_report_bytes(
    patient: Patient, file_bytes: bytes, original_filename: str, description: str = ""
) -> MedicalReport:
    """Save raw file bytes (e.g. auto-generated PDF report) directly to cloud and local storage."""
    detected = _detect_magic_type(file_bytes[:16]) or "pdf"
    stored_filename = f"{uuid.uuid4().hex}.{detected}"
    mime_type = _MIME_TYPES.get(detected, "application/pdf")
    provider = current_app.config.get("STORAGE_PROVIDER", "local")
    cloud_url = None

    # Always save a local copy if local upload folder exists
    local_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)
    try:
        with open(local_path, "wb") as f:
            f.write(file_bytes)
    except Exception as exc:
        current_app.logger.warning("Local file write error: %s", exc)

    # Cloud Storage Upload
    if provider == "firebase":
        cloud_url = _upload_to_firebase(stored_filename, file_bytes, mime_type)
        if not cloud_url:
            provider = "local"
    elif provider == "supabase":
        cloud_url = _upload_to_supabase(stored_filename, file_bytes, mime_type)
        if not cloud_url:
            provider = "local"

    report = MedicalReport(
        patient=patient,
        stored_filename=stored_filename,
        original_filename=original_filename[:255],
        file_type=detected,
        file_size=len(file_bytes),
        description=(
            v.validate_optional_text(description or "", "Description", max_length=255)
            or None
        ),
        storage_provider=provider,
        storage_url=cloud_url,
    )
    db.session.add(report)
    db.session.commit()

    log_action(
        "report_generated_cloud",
        user_id=patient.user_id,
        entity="medical_report",
        entity_id=report.id,
        details=f"{original_filename} (storage={provider})",
    )
    return report


def get_report_download_response(report: MedicalReport):
    """Return a download response (redirect to cloud URL or stream from local disk)."""
    if report.storage_provider in ("firebase", "supabase") and report.storage_url:
        return redirect(report.storage_url)

    # Local disk fallback
    full_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"], report.stored_filename
    )
    if os.path.isfile(full_path):
        return send_from_directory(
            current_app.config["UPLOAD_FOLDER"],
            report.stored_filename,
            as_attachment=True,
            download_name=report.original_filename,
        )

    # If file was marked cloud but no public URL, try redirect if url exists
    if report.storage_url:
        return redirect(report.storage_url)

    raise ReportError("The requested report file could not be found on storage.")


def delete_report(report: MedicalReport) -> None:
    """Remove a report record together with its stored file (cloud or local)."""
    if report.storage_provider == "firebase":
        _delete_from_firebase(report.stored_filename)
    elif report.storage_provider == "supabase":
        _delete_from_supabase(report.stored_filename)

    # Remove local file if present
    full_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"], report.stored_filename
    )
    if os.path.isfile(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass

    details = f"{report.original_filename} (storage={report.storage_provider})"
    user_id = report.patient.user_id if report.patient else None
    db.session.delete(report)
    db.session.commit()
    log_action(
        "report_deleted",
        user_id=user_id,
        entity="medical_report",
        entity_id=report.id,
        details=details,
    )