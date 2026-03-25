"""
MaajiKids — Blueprint: /ia
7 endpoints: recomendaciones IA (Gemini 2.5 Flash) + asistente 'Maaji'.
"""
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request
from app.extensions import db
from app.models.ai_recommendation import AIRecommendation
from app.models.evaluation import Evaluation
from app.models.child import Child
from app.models.workshop import Workshop
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.services.ai_service import generate_recommendations, chat_with_maaji
from app.utils.helpers import (
    success_response, error_response, paginate_query,
    generate_session_token, now_utc,
)
from app.utils.decorators import any_authenticated, get_current_user
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError

bp = Blueprint("ai", __name__, url_prefix="/ia")


def _get_optional_user():
    """Intenta obtener usuario autenticado sin obligar JWT."""
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            from app.models.user import User
            return db.session.get(User, int(uid))
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# RECOMENDACIONES IA
# ─────────────────────────────────────────────────────────────────────────────

# ── POST /ia/recomendaciones/generar ────────────────────────────────────────
@bp.route("/recomendaciones/generar", methods=["POST"])
@any_authenticated
def generar_recomendacion():
    """
    Genera recomendaciones IA para una evaluación vía Gemini 2.5 Flash.
    Acceso: teacher/admin.
    """
    current = get_current_user()
    if current.role_name not in ("teacher", "admin"):
        return error_response("Solo profesores o administradores pueden generar recomendaciones.", 403)

    data = request.get_json(silent=True) or {}
    evaluation_id = data.get("evaluation_id")
    if not evaluation_id:
        return error_response("Se requiere evaluation_id.", 400)

    ev = db.session.get(Evaluation, int(evaluation_id))
    if not ev:
        return error_response("Evaluación no encontrada.", 404)

    if current.role_name == "teacher" and ev.teacher_id != current.id:
        return error_response("No tienes acceso a esta evaluación.", 403)

    # Verificar si ya existe recomendación para esta evaluación
    existing = AIRecommendation.query.filter_by(evaluation_id=ev.id).first()
    if existing and not data.get("regenerar", False):
        return error_response(
            "Ya existe una recomendación para esta evaluación. Envía 'regenerar': true para sobrescribir.", 409
        )

    child = db.session.get(Child, ev.child_id)
    workshop = db.session.get(Workshop, ev.workshop_id)

    # Llamar a Gemini
    text = generate_recommendations(
        child_name=child.full_name if child else "N/A",
        age_months=child.age_in_months if child else 0,
        score_cognitive=float(ev.score_cognitive),
        score_motor=float(ev.score_motor),
        score_language=float(ev.score_language),
        score_social=float(ev.score_social),
        observations=ev.observations,
        workshop_title=workshop.title if workshop else "",
    )

    if not text:
        return error_response("Error al generar recomendaciones con IA. Intenta nuevamente.", 502)

    if existing and data.get("regenerar", False):
        existing.recommendations_text = text
        existing.generated_at = now_utc()
        rec = existing
    else:
        rec = AIRecommendation(
            evaluation_id=ev.id,
            child_id=ev.child_id,
            recommendations_text=text,
            is_visible_to_parent=True,
            model_used="gemini-2.5-flash",
        )
        db.session.add(rec)

    db.session.commit()
    return success_response(rec.to_dict(), "Recomendaciones generadas exitosamente.", 201)


# ── GET /ia/recomendaciones/nino/:id ────────────────────────────────────────
@bp.route("/recomendaciones/nino/<int:child_id>", methods=["GET"])
@any_authenticated
def list_recommendations(child_id):
    """
    Lista recomendaciones del niño.
    Parent solo ve las con is_visible_to_parent=True.
    """
    current = get_current_user()
    role = current.role_name

    child = db.session.get(Child, child_id)
    if not child or not child.is_active:
        return error_response("Niño no encontrado.", 404)

    if role == "parent" and child.parent_id != current.id:
        return error_response("No tienes acceso a este niño.", 403)
    if role == "teacher":
        teacher_ws_ids = {ws.id for ws in Workshop.query.filter_by(teacher_id=current.id).all()}
        from app.models.enrollment import Enrollment
        child_ws_ids = {e.workshop_id for e in child.enrollments.filter_by(status="active")}
        if not (teacher_ws_ids & child_ws_ids):
            return error_response("No tienes acceso a las recomendaciones de este niño.", 403)

    q = AIRecommendation.query.filter_by(child_id=child_id)
    if role == "parent":
        q = q.filter_by(is_visible_to_parent=True)

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    q = q.order_by(AIRecommendation.generated_at.desc())
    result = paginate_query(q, page, per_page)
    result["items"] = [r.to_dict() for r in result["items"]]
    return success_response(result)


# ── GET /ia/recomendaciones/:id ──────────────────────────────────────────────
@bp.route("/recomendaciones/<int:rec_id>", methods=["GET"])
@any_authenticated
def get_recommendation(rec_id):
    """Detalle de una recomendación IA."""
    current = get_current_user()
    role = current.role_name

    rec = db.session.get(AIRecommendation, rec_id)
    if not rec:
        return error_response("Recomendación no encontrada.", 404)

    if role == "parent":
        child = db.session.get(Child, rec.child_id)
        if not child or child.parent_id != current.id:
            return error_response("Sin acceso.", 403)
        if not rec.is_visible_to_parent:
            return error_response("Esta recomendación no está disponible.", 403)
    elif role == "teacher":
        ev = db.session.get(Evaluation, rec.evaluation_id)
        if not ev or ev.teacher_id != current.id:
            return error_response("Sin acceso.", 403)

    return success_response(rec.to_dict())


# ── PATCH /ia/recomendaciones/:id ────────────────────────────────────────────
@bp.route("/recomendaciones/<int:rec_id>", methods=["PATCH"])
@any_authenticated
def update_recommendation(rec_id):
    """
    Actualiza recomendación. Incluye campo is_visible_to_parent.
    Solo admin.
    """
    current = get_current_user()
    if current.role_name != "admin":
        return error_response("Solo el administrador puede editar recomendaciones.", 403)

    rec = db.session.get(AIRecommendation, rec_id)
    if not rec:
        return error_response("Recomendación no encontrada.", 404)

    data = request.get_json(silent=True) or {}
    if "recommendations_text" in data:
        rec.recommendations_text = data["recommendations_text"]
    if "is_visible_to_parent" in data:
        rec.is_visible_to_parent = bool(data["is_visible_to_parent"])

    db.session.commit()
    return success_response(rec.to_dict(), "Recomendación actualizada exitosamente.")


# ── DELETE /ia/recomendaciones/:id ───────────────────────────────────────────
@bp.route("/recomendaciones/<int:rec_id>", methods=["DELETE"])
@any_authenticated
def delete_recommendation(rec_id):
    """Elimina una recomendación IA. Solo admin."""
    current = get_current_user()
    if current.role_name != "admin":
        return error_response("Solo el administrador puede eliminar recomendaciones.", 403)

    rec = db.session.get(AIRecommendation, rec_id)
    if not rec:
        return error_response("Recomendación no encontrada.", 404)

    db.session.delete(rec)
    db.session.commit()
    return success_response(message="Recomendación eliminada exitosamente.")


# ─────────────────────────────────────────────────────────────────────────────
# ASISTENTE MAAJI
# ─────────────────────────────────────────────────────────────────────────────

# ── POST /ia/chat ────────────────────────────────────────────────────────────
@bp.route("/chat", methods=["POST"])
def chat():
    """
    Chat con el asistente 'Maaji'. Público (sin login).
    Acepta session_token anónimo o JWT. Auto-eliminado a las 2 horas.
    Body: {mensaje: str, session_token?: str}
    """
    current_user = _get_optional_user()
    data = request.get_json(silent=True) or {}
    mensaje = data.get("mensaje", "").strip()
    session_token_input = data.get("session_token")

    if not mensaje:
        return error_response("El campo 'mensaje' es requerido.", 400)
    if len(mensaje) > 2000:
        return error_response("El mensaje no puede superar los 2000 caracteres.", 400)

    # Obtener o crear sesión de chat
    session: ChatSession | None = None

    if current_user:
        # Usuario autenticado: buscar sesión activa del usuario
        session = ChatSession.query.filter_by(user_id=current_user.id).order_by(
            ChatSession.created_at.desc()
        ).first()
        if not session:
            token = generate_session_token()
            session = ChatSession(
                session_token=token,
                user_id=current_user.id,
            )
            db.session.add(session)
            db.session.flush()
    elif session_token_input:
        # Sesión anónima con token existente
        session = ChatSession.query.filter_by(session_token=session_token_input).first()

    if not session:
        # Nueva sesión anónima
        token = generate_session_token()
        session = ChatSession(
            session_token=token,
            user_id=current_user.id if current_user else None,
        )
        db.session.add(session)
        db.session.flush()

    # Obtener historial de la sesión (máx. últimos 20 mensajes)
    prev_messages = ChatMessage.query.filter_by(sesion_id=session.id).order_by(
        ChatMessage.created_at.asc()
    ).limit(20).all()

    # Construir historial para Gemini
    history = []
    for msg in prev_messages:
        role_gemini = "user" if msg.role == "user" else "model"
        history.append({"role": role_gemini, "parts": [{"text": msg.content}]})

    # Agregar el mensaje actual
    history.append({"role": "user", "parts": [{"text": mensaje}]})

    # Contexto de talleres activos
    active_workshops = []
    try:
        ws_list = Workshop.query.filter_by(is_active=True).limit(15).all()
        active_workshops = [
            {
                "title": w.title,
                "age_min": w.age_min,
                "age_max": w.age_max,
                "price": float(w.price),
                "available_spots": w.available_spots,
                "schedule": w.schedule,
            }
            for w in ws_list
        ]
    except Exception:
        pass

    # Hijos del padre autenticado (si aplica)
    parent_children = []
    if current_user and current_user.role_name == "parent":
        try:
            children = Child.query.filter_by(parent_id=current_user.id, is_active=True).all()
            parent_children = [{"full_name": c.full_name, "age_months": c.age_in_months} for c in children]
        except Exception:
            pass

    # Llamar a Gemini
    respuesta = chat_with_maaji(history, active_workshops, parent_children)
    if not respuesta:
        return error_response("Error al conectar con el asistente IA. Intenta nuevamente.", 502)

    # Guardar mensaje del usuario y respuesta
    user_msg = ChatMessage(sesion_id=session.id, role="user", content=mensaje)
    assistant_msg = ChatMessage(sesion_id=session.id, role="assistant", content=respuesta)
    db.session.add_all([user_msg, assistant_msg])

    session.last_message_at = now_utc()
    db.session.commit()

    return success_response({
        "respuesta": respuesta,
        "session_token": session.session_token,
        "sesion_id": session.id,
    })


# ── GET /ia/chat/historial ───────────────────────────────────────────────────
@bp.route("/chat/historial", methods=["GET"])
@any_authenticated
def chat_historial():
    """
    Sin ?sesion_id: lista sesiones del usuario.
    Con ?sesion_id=X: retorna mensajes de esa sesión.
    Acceso: parent/admin.
    """
    current = get_current_user()
    if current.role_name not in ("parent", "admin"):
        return error_response("Sin permisos.", 403)

    sesion_id = request.args.get("sesion_id", type=int)
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    if sesion_id:
        session = db.session.get(ChatSession, sesion_id)
        if not session:
            return error_response("Sesión no encontrada.", 404)
        if current.role_name == "parent" and session.user_id != current.id:
            return error_response("Sin acceso a esta sesión.", 403)
        messages = ChatMessage.query.filter_by(sesion_id=sesion_id).order_by(
            ChatMessage.created_at.asc()
        ).all()
        return success_response({
            "sesion": session.to_dict(),
            "mensajes": [m.to_dict() for m in messages],
        })
    else:
        q = ChatSession.query
        if current.role_name == "parent":
            q = q.filter_by(user_id=current.id)
        q = q.order_by(ChatSession.created_at.desc())
        result = paginate_query(q, page, per_page)
        result["items"] = [s.to_dict() for s in result["items"]]
        return success_response(result)
