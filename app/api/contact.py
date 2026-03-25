"""
MaajiKids — Blueprint: /contacto
4 endpoints. PATCH unifica actualización de estado y envío de respuesta por email.
"""
from datetime import datetime, timezone
from flask import Blueprint, request
from app.extensions import db
from app.models.contact_message import ContactMessage
from app.services.email_service import send_contact_reply_email
from app.utils.helpers import (
    to_upper, normalize_email, success_response, error_response,
    paginate_query, now_utc,
)
from app.utils.decorators import any_authenticated, get_current_user

bp = Blueprint("contact", __name__, url_prefix="/contacto")

VALID_STATUSES = ("unread", "read", "replied")


# ── POST /contacto/ ──────────────────────────────────────────────────────────
@bp.route("/", methods=["POST"])
def send_contact():
    """Envía un mensaje de consulta al centro. No requiere login."""
    data = request.get_json(silent=True) or {}

    sender_name = to_upper(data.get("sender_name", ""))
    sender_email = normalize_email(data.get("sender_email", ""))
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()

    if not all([sender_name, sender_email, subject, body]):
        return error_response("Campos requeridos: sender_name, sender_email, subject, body.", 400)
    if "@" not in sender_email:
        return error_response("Email inválido.", 400)
    if len(body) < 10:
        return error_response("El mensaje debe tener al menos 10 caracteres.", 400)

    msg = ContactMessage(
        sender_name=sender_name,
        sender_email=sender_email,
        subject=subject,
        body=body,
        status="unread",
    )
    db.session.add(msg)
    db.session.commit()

    return success_response(
        {"id": msg.id},
        "Mensaje enviado exitosamente. El equipo de MaajiKids te responderá pronto.",
        201,
    )


# ── GET /contacto/ ───────────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
@any_authenticated
def list_messages():
    """Lista mensajes de contacto. Solo admin/secretary."""
    current = get_current_user()
    if current.role_name not in ("admin", "secretary"):
        return error_response("Sin permisos.", 403)

    estado = request.args.get("estado")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    q = ContactMessage.query
    if estado:
        if estado not in VALID_STATUSES:
            return error_response(f"Estado inválido. Use: {', '.join(VALID_STATUSES)}.", 400)
        q = q.filter_by(status=estado)

    q = q.order_by(ContactMessage.created_at.desc())
    result = paginate_query(q, page, per_page)
    result["items"] = [m.to_dict() for m in result["items"]]
    return success_response(result)


# ── GET /contacto/:id ────────────────────────────────────────────────────────
@bp.route("/<int:msg_id>", methods=["GET"])
@any_authenticated
def get_message(msg_id):
    """Detalle de un mensaje de contacto. Solo admin/secretary."""
    current = get_current_user()
    if current.role_name not in ("admin", "secretary"):
        return error_response("Sin permisos.", 403)

    msg = db.session.get(ContactMessage, msg_id)
    if not msg:
        return error_response("Mensaje no encontrado.", 404)

    # Auto-marcar como leído al abrir
    if msg.status == "unread":
        msg.status = "read"
        db.session.commit()

    return success_response(msg.to_dict())


# ── PATCH /contacto/:id ──────────────────────────────────────────────────────
@bp.route("/<int:msg_id>", methods=["PATCH"])
@any_authenticated
def update_message(msg_id):
    """
    Unifica actualización de estado y envío de respuesta.
    - Si body incluye reply_text → envía email al remitente + status='replied'.
    - Si solo incluye status → actualiza estado.
    Solo admin/secretary.
    """
    current = get_current_user()
    if current.role_name not in ("admin", "secretary"):
        return error_response("Sin permisos.", 403)

    msg = db.session.get(ContactMessage, msg_id)
    if not msg:
        return error_response("Mensaje no encontrado.", 404)

    data = request.get_json(silent=True) or {}
    reply_text = data.get("reply_text", "").strip()
    new_status = data.get("status")

    if reply_text:
        # Enviar respuesta por email
        sent = send_contact_reply_email(
            msg.sender_email, msg.sender_name, msg.subject, reply_text
        )
        msg.reply_text = reply_text
        msg.status = "replied"
        msg.replied_by = current.id
        msg.replied_at = now_utc()

        db.session.commit()
        return success_response(
            msg.to_dict(),
            "Respuesta enviada exitosamente." + (" (Email enviado.)" if sent else " (Advertencia: email no pudo enviarse.)"),
        )

    elif new_status:
        if new_status not in VALID_STATUSES:
            return error_response(f"Estado inválido. Use: {', '.join(VALID_STATUSES)}.", 400)
        msg.status = new_status
        db.session.commit()
        return success_response(msg.to_dict(), "Estado actualizado exitosamente.")

    else:
        return error_response("Se requiere 'reply_text' o 'status' en el body.", 400)


# ── DELETE /contacto/:id ─────────────────────────────────────────────────────
@bp.route("/<int:msg_id>", methods=["DELETE"])
@any_authenticated
def delete_message(msg_id):
    """Elimina un mensaje de contacto. Solo admin."""
    current = get_current_user()
    if current.role_name != "admin":
        return error_response("Solo el administrador puede eliminar mensajes.", 403)

    msg = db.session.get(ContactMessage, msg_id)
    if not msg:
        return error_response("Mensaje no encontrado.", 404)

    db.session.delete(msg)
    db.session.commit()
    return success_response(message="Mensaje eliminado exitosamente.")
