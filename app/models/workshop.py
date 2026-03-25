"""
Tabla: workshops
Talleres del centro. Visible públicamente sin login.
"""
from datetime import datetime, timezone
from app.extensions import db


class Workshop(db.Model):
    __tablename__ = "workshops"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)            # MAYÚSCULAS
    description = db.Column(db.Text, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    schedule = db.Column(db.String(200), nullable=False)          # MAYÚSCULAS
    age_min = db.Column(db.Integer, nullable=False)               # en meses
    age_max = db.Column(db.Integer, nullable=False)               # en meses (max 72)
    max_capacity = db.Column(db.Integer, nullable=False)
    current_enrolled = db.Column(db.Integer, default=0, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)          # Cloudinary
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    teacher = db.relationship("User", foreign_keys=[teacher_id], lazy="joined")
    enrollments = db.relationship("Enrollment", back_populates="workshop", lazy="dynamic")
    evaluations = db.relationship("Evaluation", back_populates="workshop", lazy="dynamic")
    order_items = db.relationship("OrderItem", back_populates="workshop", lazy="dynamic")

    def __repr__(self):
        return f"<Workshop {self.title}>"

    @property
    def available_spots(self) -> int:
        return max(0, self.max_capacity - self.current_enrolled)

    @property
    def is_full(self) -> bool:
        return self.current_enrolled >= self.max_capacity

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "teacher": {
                "id": self.teacher.id,
                "full_name": self.teacher.full_name,
            } if self.teacher else None,
            "schedule": self.schedule,
            "age_min": self.age_min,
            "age_max": self.age_max,
            "age_range": f"{self.age_min // 12}a {self.age_min % 12}m - {self.age_max // 12}a {self.age_max % 12}m",
            "max_capacity": self.max_capacity,
            "current_enrolled": self.current_enrolled,
            "available_spots": self.available_spots,
            "price": float(self.price),
            "image_url": self.image_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
