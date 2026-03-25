"""
Tabla: chat_mensajes
Mensajes del asistente IA Maaji. Se eliminan en cascada con la sesión.
"""
from datetime import datetime, timezone
from app.extensions import db


class ChatMessage(db.Model):
    __tablename__ = "chat_mensajes"

    id = db.Column(db.Integer, primary_key=True)
    sesion_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_sesiones.id", ondelete="CASCADE"),
        nullable=False
    )
    role = db.Column(db.String(20), nullable=False)    # 'user' | 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    session = db.relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage sesion={self.sesion_id} role={self.role}>"

    def to_dict(self):
        return {
            "id": self.id,
            "sesion_id": self.sesion_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
