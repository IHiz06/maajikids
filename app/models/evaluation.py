"""
Tabla: evaluations
Evaluaciones de desarrollo infantil en 4 dominios (0-10).
"""
from datetime import datetime, timezone
from app.extensions import db


class Evaluation(db.Model):
    __tablename__ = "evaluations"

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    eval_date = db.Column(db.Date, nullable=False)
    score_cognitive = db.Column(db.Numeric(4, 1), nullable=False)    # 0.0 – 10.0
    score_motor = db.Column(db.Numeric(4, 1), nullable=False)
    score_language = db.Column(db.Numeric(4, 1), nullable=False)
    score_social = db.Column(db.Numeric(4, 1), nullable=False)
    observations = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    child = db.relationship("Child", back_populates="evaluations", lazy="joined")
    workshop = db.relationship("Workshop", back_populates="evaluations", lazy="joined")
    teacher = db.relationship("User", back_populates="evaluations_given",
                              foreign_keys=[teacher_id], lazy="joined")
    ai_recommendation = db.relationship("AIRecommendation", back_populates="evaluation",
                                        uselist=False, lazy="joined")

    def __repr__(self):
        return f"<Evaluation child={self.child_id} date={self.eval_date}>"

    @property
    def average_score(self) -> float:
        scores = [
            float(self.score_cognitive),
            float(self.score_motor),
            float(self.score_language),
            float(self.score_social),
        ]
        return round(sum(scores) / len(scores), 2)

    def to_dict(self):
        return {
            "id": self.id,
            "child_id": self.child_id,
            "child_name": self.child.full_name if self.child else None,
            "workshop_id": self.workshop_id,
            "workshop_title": self.workshop.title if self.workshop else None,
            "teacher_id": self.teacher_id,
            "teacher_name": self.teacher.full_name if self.teacher else None,
            "eval_date": self.eval_date.isoformat() if self.eval_date else None,
            "scores": {
                "cognitive": float(self.score_cognitive),
                "motor": float(self.score_motor),
                "language": float(self.score_language),
                "social": float(self.score_social),
                "average": self.average_score,
            },
            "observations": self.observations,
            "has_recommendation": self.ai_recommendation is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
