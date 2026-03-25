"""
Tabla: users
Usuarios del sistema (admin, teacher, secretary, parent).
"""
from datetime import datetime, timezone
import bcrypt
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)          # minúsculas (excepción)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)                   # MAYÚSCULAS
    last_name = db.Column(db.String(100), nullable=False)                    # MAYÚSCULAS
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_code = db.Column(db.String(10), nullable=True)
    verification_expires = db.Column(db.DateTime, nullable=True)
    last_activity = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relaciones
    role = db.relationship("Role", foreign_keys=[role_id], back_populates="users", lazy="joined", overlaps="creator")
    children = db.relationship("Child", back_populates="parent", lazy="dynamic",
                               foreign_keys="Child.parent_id")
    orders = db.relationship("Order", back_populates="parent", lazy="dynamic")
    evaluations_given = db.relationship("Evaluation", back_populates="teacher",
                                        lazy="dynamic", foreign_keys="Evaluation.teacher_id")
    contact_replies = db.relationship("ContactMessage", back_populates="replied_by_user",
                                      lazy="dynamic", foreign_keys="ContactMessage.replied_by")
    token_blacklist = db.relationship("TokenBlacklist", back_populates="user", lazy="dynamic")
    chat_sessions = db.relationship("ChatSession", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"

    # ── Contraseña ─────────────────────────────────────────────────────────
    def set_password(self, password: str) -> None:
        """Hash bcrypt con costo 12."""
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    # ── Helpers ────────────────────────────────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def role_name(self) -> str:
        return self.role.name.lower() if self.role else ""

    def update_activity(self):
        self.last_activity = datetime.utcnow()

    def to_dict(self, include_sensitive=False):
        data = {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "role": self.role.to_dict() if self.role else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
        return data
