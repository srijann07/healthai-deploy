from datetime import datetime, timezone

from extensions import db


class MedicalReport(db.Model):
    """A file (PDF/JPG/PNG) uploaded by a patient."""

    __tablename__ = "medical_reports"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True
    )
    patient = db.relationship("Patient", back_populates="medical_reports")

    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # pdf / jpg / png
    file_size = db.Column(db.Integer, nullable=False)  # bytes
    description = db.Column(db.String(255))
    storage_provider = db.Column(db.String(20), default="local", nullable=False)
    storage_url = db.Column(db.String(512))

    uploaded_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    @property
    def size_display(self) -> str:
        size = self.file_size or 0
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    def __repr__(self) -> str:
        return f"<MedicalReport #{self.id} {self.original_filename}>"
