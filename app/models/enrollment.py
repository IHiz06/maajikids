"""
Tabla: enrollments
Inscripciones activas de niños en talleres (post-pago aprobado).
"""
from datetime import datetime, timezone
from app.extensions import db


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)  # 'active' | 'cancelled'
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("child_id", "workshop_id", name="uq_enrollment_child_workshop"),
    )

    # Relaciones
    child = db.relationship("Child", back_populates="enrollments", lazy="joined")
    workshop = db.relationship("Workshop", back_populates="enrollments", lazy="joined")
    order = db.relationship("Order", lazy="joined")

    def __repr__(self):
        return f"<Enrollment child={self.child_id} workshop={self.workshop_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "child_id": self.child_id,
            "child_name": self.child.full_name if self.child else None,
            "workshop_id": self.workshop_id,
            "workshop_title": self.workshop.title if self.workshop else None,
            "order_id": self.order_id,
            "status": self.status,
            "enrolled_at": self.enrolled_at.isoformat() if self.enrolled_at else None,
        }
