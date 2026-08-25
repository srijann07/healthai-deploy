from extensions import db


class Role(db.Model):
    """User roles: patient, doctor, admin."""

    __tablename__ = "roles"

    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"
    ALL = (PATIENT, DOCTOR, ADMIN)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"

    @classmethod
    def get_by_name(cls, name: str) -> "Role | None":
        return cls.query.filter_by(name=name).first()

    @classmethod
    def seed_defaults(cls) -> None:
        """Insert the three platform roles if they do not exist yet."""
        defaults = {
            cls.PATIENT: "Can submit symptoms, receive AI predictions and upload reports.",
            cls.DOCTOR: "Can review patients, verify AI predictions and add recommendations.",
            cls.ADMIN: "Full platform management access.",
        }
        for name, description in defaults.items():
            if not cls.get_by_name(name):
                db.session.add(cls(name=name, description=description))
        db.session.commit()
