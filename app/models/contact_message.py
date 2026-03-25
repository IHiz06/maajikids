"""
Tabla: contact_messages
Mensajes de contacto enviados desde la web pública.
"""
from datetime import datetime, timezone
from app.extensions import db


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_name = db.Column(db.String(200), nullable=False)       # MAYÚSCULAS
    sender_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(20), default="unread", nullable=False
    )  # 'unread' | 'read' | 'replied'
    reply_text = db.Column(db.Text, nullable=True)
    replied_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    replied_by_user = db.relationship("User", back_populates="contact_replies",
                                      foreign_keys=[replied_by], lazy="joined")

    def __repr__(self):
        return f"<ContactMessage from={self.sender_email} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "sender_name": self.sender_name,
            "sender_email": self.sender_email,
            "subject": self.subject,
            "body": self.body,
            "status": self.status,
            "reply_text": self.reply_text,
            "replied_by": self.replied_by,
            "replied_by_name": self.replied_by_user.full_name if self.replied_by_user else None,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
