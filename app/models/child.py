"""
Tabla: children
Niños registrados por padres. Datos médicos cifrados con AES-256.
"""
from datetime import datetime, timezone, date
from app.extensions import db


class Child(db.Model):
    __tablename__ = "children"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)         # MAYÚSCULAS
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)             # 'M' | 'F' | 'OTRO'
    photo_url = db.Column(db.String(500), nullable=True)          # Cloudinary
    medical_info = db.Column(db.Text, nullable=True)              # cifrado AES-256
    allergies = db.Column(db.Text, nullable=True)                 # cifrado AES-256
    payment_status = db.Column(
        db.String(20),
        default="none",
        nullable=False
    )  # 'none' | 'pending' | 'verified'
    #dni_document_url = db.Column(db.String(500), nullable=True)   # Supabase Storage
    dni_document_url = db.Column(db.Text, nullable=True)
    dni_uploaded_by = db.Column(db.String(20), nullable=True)     # 'parent' | 'admin' | 'secretary'
    dni_verified = db.Column(db.Boolean, default=False, nullable=False)
    dni_pending_review = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    parent = db.relationship("User", back_populates="children", foreign_keys=[parent_id], lazy="joined")
    emergency_contacts = db.relationship("EmergencyContact", back_populates="child",
                                         lazy="dynamic", cascade="all, delete-orphan",
                                         order_by="EmergencyContact.order_index")
    enrollments = db.relationship("Enrollment", back_populates="child", lazy="dynamic")
    evaluations = db.relationship("Evaluation", back_populates="child", lazy="dynamic")
    ai_recommendations = db.relationship("AIRecommendation", back_populates="child", lazy="dynamic")
    order_items = db.relationship("OrderItem", back_populates="child", lazy="dynamic")

    def __repr__(self):
        return f"<Child {self.full_name}>"

    @property
    def age_in_months(self) -> int:
        """Calcula edad en meses desde fecha de nacimiento."""
        today = date.today()
        dob = self.date_of_birth
        months = (today.year - dob.year) * 12 + (today.month - dob.month)
        if today.day < dob.day:
            months -= 1
        return max(0, months)

    @property
    def age_in_years(self) -> float:
        return round(self.age_in_months / 12, 1)

    def to_dict(self, include_medical=False):
        data = {
            "id": self.id,
            "parent_id": self.parent_id,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "age_months": self.age_in_months,
            "age_years": self.age_in_years,
            "gender": self.gender,
            "photo_url": self.photo_url,
            "payment_status": self.payment_status,
            "dni_document_url": self.dni_document_url,
            "dni_uploaded_by": self.dni_uploaded_by,
            "dni_verified": self.dni_verified,
            "dni_pending_review": self.dni_pending_review,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_medical:
            # medical_info y allergies ya descifrados desde el servicio
            data["medical_info"] = self.medical_info
            data["allergies"] = self.allergies
        return data
