"""
Tabla: emergency_contacts
Contactos de emergencia de los niños (máximo 3 por niño).
"""
from app.extensions import db


class EmergencyContact(db.Model):
    __tablename__ = "emergency_contacts"

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)          # MAYÚSCULAS
    phone = db.Column(db.String(20), nullable=False)
    relationship = db.Column(db.String(100), nullable=False)       # MAYÚSCULAS
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    order_index = db.Column(db.Integer, default=1, nullable=False)

    # Relaciones
    child = db.relationship("Child", back_populates="emergency_contacts")

    def __repr__(self):
        return f"<EmergencyContact {self.full_name} - {self.relationship}>"

    def to_dict(self):
        return {
            "id": self.id,
            "child_id": self.child_id,
            "full_name": self.full_name,
            "phone": self.phone,
            "relationship": self.relationship,
            "is_primary": self.is_primary,
            "order_index": self.order_index,
        }
