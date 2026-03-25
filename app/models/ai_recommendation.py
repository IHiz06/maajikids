"""
Tabla: ai_recommendations
Recomendaciones generadas por Gemini 2.5 Flash basadas en evaluaciones.
"""
from datetime import datetime, timezone
from app.extensions import db


class AIRecommendation(db.Model):
    __tablename__ = "ai_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey("evaluations.id"), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False)
    recommendations_text = db.Column(db.Text, nullable=False)
    is_visible_to_parent = db.Column(db.Boolean, default=True, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    model_used = db.Column(db.String(100), default="gemini-2.5-flash", nullable=False)

    # Relaciones
    evaluation = db.relationship("Evaluation", back_populates="ai_recommendation")
    child = db.relationship("Child", back_populates="ai_recommendations", lazy="joined")

    def __repr__(self):
        return f"<AIRecommendation eval={self.evaluation_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "evaluation_id": self.evaluation_id,
            "child_id": self.child_id,
            "child_name": self.child.full_name if self.child else None,
            "recommendations_text": self.recommendations_text,
            "is_visible_to_parent": self.is_visible_to_parent,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "model_used": self.model_used,
        }
