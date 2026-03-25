"""
Tabla: chat_sesiones
Sesiones del asistente IA Maaji. Anónimas o autenticadas.
Auto-eliminadas a las 2 horas por APScheduler.
"""
from datetime import datetime, timezone
from app.extensions import db


class ChatSession(db.Model):
    __tablename__ = "chat_sesiones"

    id = db.Column(db.Integer, primary_key=True)
    session_token = db.Column(db.String(200), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_message_at = db.Column(db.DateTime, nullable=True)

    # Relaciones
    user = db.relationship("User", back_populates="chat_sessions")
    messages = db.relationship("ChatMessage", back_populates="session",
                               lazy="dynamic", cascade="all, delete-orphan",
                               order_by="ChatMessage.created_at")

    def __repr__(self):
        return f"<ChatSession token={self.session_token[:8]}...>"

    def to_dict(self, include_messages=False):
        data = {
            "id": self.id,
            "session_token": self.session_token,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data
