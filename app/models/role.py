"""
Tabla: roles
Roles del sistema (admin, teacher, secretary, parent) y roles personalizados.
"""
from datetime import datetime, timezone
from app.extensions import db


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    permissions = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relaciones
    # users: todos los usuarios con este rol (FK desde User.role_id → roles.id)
    users = db.relationship(
        "User",
        foreign_keys="[User.role_id]",
        back_populates="role",
        lazy="dynamic",
        overlaps="creator",
    )
    # creator: el admin que creó el rol personalizado (FK desde roles.created_by → users.id)
    creator = db.relationship(
        "User",
        foreign_keys=[created_by],
        lazy="select",
        overlaps="users",
    )

    # ── Roles del sistema predefinidos ──────────────────────────────────
    SYSTEM_ROLES = {
        "admin": {
            "workshops": {"read": True, "write": True, "delete": True},
            "children": {"read": True, "write": True, "delete": True},
            "evaluations": {"read": True, "write": True, "delete": True},
            "payments": {"read": True, "write": True, "delete": True},
            "users": {"read": True, "write": True, "delete": True},
            "reports": {"read": True},
            "contact": {"read": True, "write": True, "delete": True},
            "ai": {"read": True, "write": True},
            "roles": {"read": True, "write": True, "delete": True},
        },
        "teacher": {
            "workshops": {"read": True, "write": False, "delete": False},
            "children": {"read": True, "write": False, "delete": False},
            "evaluations": {"read": True, "write": True, "delete": False},
            "payments": {"read": False, "write": False, "delete": False},
            "users": {"read": False, "write": False, "delete": False},
            "reports": {"read": True},
            "contact": {"read": False, "write": False, "delete": False},
            "ai": {"read": True, "write": True},
        },
        "secretary": {
            "workshops": {"read": True, "write": False, "delete": False},
            "children": {"read": True, "write": True, "delete": False},
            "evaluations": {"read": False, "write": False, "delete": False},
            "payments": {"read": True, "write": False, "delete": False},
            "users": {"read": False, "write": False, "delete": False},
            "reports": {"read": True},
            "contact": {"read": True, "write": True, "delete": False},
            "ai": {"read": False, "write": False},
        },
        "parent": {
            "workshops": {"read": True, "write": False, "delete": False},
            "children": {"read": True, "write": True, "delete": False},
            "evaluations": {"read": True, "write": False, "delete": False},
            "payments": {"read": True, "write": True, "delete": False},
            "users": {"read": False, "write": False, "delete": False},
            "reports": {"read": True},
            "contact": {"read": False, "write": True, "delete": False},
            "ai": {"read": True, "write": True},
        },
    }

    def __repr__(self):
        return f"<Role {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
