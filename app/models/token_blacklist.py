"""
Tabla: token_blacklist
JTIs de tokens JWT revocados. APScheduler limpia expirados cada hora.
"""
from datetime import datetime, timezone
from app.extensions import db


class TokenBlacklist(db.Model):
    __tablename__ = "token_blacklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(200), unique=True, nullable=False)
    token_type = db.Column(db.String(20), nullable=False)   # 'access' | 'refresh'
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    # Relaciones
    user = db.relationship("User", back_populates="token_blacklist")

    def __repr__(self):
        return f"<TokenBlacklist jti={self.jti[:8]}...>"
