"""
Tablas: orders, order_items
Carrito de compras y órdenes de MercadoPago.
"""
from datetime import datetime, timezone
from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # 'pending' | 'approved' | 'rejected' | 'cancelled'
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    mp_preference_id = db.Column(db.String(200), nullable=True)
    mp_payment_id = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)

    # Relaciones
    parent = db.relationship("User", back_populates="orders", lazy="joined")
    items = db.relationship("OrderItem", back_populates="order", lazy="joined",
                            cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "status": self.status,
            "total_amount": float(self.total_amount),
            "mp_preference_id": self.mp_preference_id,
            "mp_payment_id": self.mp_payment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("child_id", "workshop_id", name="uq_order_item_child_workshop"),
    )

    # Relaciones
    order = db.relationship("Order", back_populates="items")
    child = db.relationship("Child", back_populates="order_items", lazy="joined")
    workshop = db.relationship("Workshop", back_populates="order_items", lazy="joined")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} child={self.child_id} workshop={self.workshop_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "child_id": self.child_id,
            "child_name": self.child.full_name if self.child else None,
            "workshop_id": self.workshop_id,
            "workshop_title": self.workshop.title if self.workshop else None,
            "unit_price": float(self.unit_price),
        }
