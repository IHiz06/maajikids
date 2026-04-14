"""
MaajiKids — Blueprint: /ninos/<id>/contactos-emergencia
4 endpoints. Máximo 3 contactos por niño.
"""
from flask import Blueprint, request
from app.extensions import db
from app.models.child import Child
from app.models.emergency_contact import EmergencyContact
from app.utils.helpers import to_upper, success_response, error_response
from app.utils.decorators import any_authenticated, get_current_user

bp = Blueprint("emergency_contacts", __name__, url_prefix="/ninos/<int:child_id>/contactos-emergencia")

MAX_CONTACTS = 3


def _check_child_access(current_user, child_id: int, write: bool = False):
    """Verifica acceso del usuario al niño. Retorna (child, error_response)."""
    child = db.session.get(Child, child_id)
    if not child or not child.is_active:
        return None, error_response("Niño no encontrado.", 404)

    role = current_user.role_name
    if role == "parent" and child.parent_id != current_user.id:
        return None, error_response("No tienes acceso a este niño.", 403)
    if role not in ("parent", "admin", "secretary", "teacher"):
        return None, error_response("Sin permisos.", 403)

    return child, None


# ── GET /ninos/:id/contactos-emergencia ──────────────────────────────────────
@bp.route("/", methods=["GET"])
@any_authenticated
def list_contacts(child_id):
    """Lista contactos de emergencia del niño (máx. 3)."""
    current = get_current_user()
    child, err = _check_child_access(current, child_id)
    if err:
        return err

    contacts = EmergencyContact.query.filter_by(child_id=child_id).order_by(
        EmergencyContact.order_index
    ).all()
    return success_response([c.to_dict() for c in contacts])


# ── POST /ninos/:id/contactos-emergencia ─────────────────────────────────────
@bp.route("/", methods=["POST"])
@any_authenticated
def create_contact(child_id):
    """Agrega un contacto de emergencia. Valida máximo 3."""
    current = get_current_user()
    child, err = _check_child_access(current, child_id, write=True)
    if err:
        return err

    existing_count = EmergencyContact.query.filter_by(child_id=child_id).count()
    if existing_count >= MAX_CONTACTS:
        return error_response(f"Máximo {MAX_CONTACTS} contactos de emergencia por niño.", 400)

    data = request.get_json(silent=True) or {}
    full_name = to_upper(data.get("full_name", ""))
    phone = data.get("phone", "")
    relationship = to_upper(data.get("relationship", ""))
    is_primary = data.get("is_primary", False)

    if not full_name or not phone or not relationship:
        return error_response("Campos requeridos: full_name, phone, relationship.", 400)

    # Si se marca como primario, quitar primario de los demás
    if is_primary:
        EmergencyContact.query.filter_by(child_id=child_id, is_primary=True).update(
            {"is_primary": False}
        )

    contact = EmergencyContact(
        child_id=child_id,
        full_name=full_name,
        phone=phone,
        relationship=relationship,
        is_primary=bool(is_primary),
        order_index=existing_count + 1,
    )
    db.session.add(contact)
    db.session.commit()
    return success_response(contact.to_dict(), "Contacto de emergencia agregado.", 201)


# ── PATCH /ninos/:id/contactos-emergencia/:cid ───────────────────────────────
@bp.route("/<int:contact_id>", methods=["PATCH"])
@any_authenticated
def update_contact(child_id, contact_id):
    """Actualiza datos de un contacto de emergencia."""
    current = get_current_user()
    child, err = _check_child_access(current, child_id, write=True)
    if err:
        return err

    # Secretary no puede editar contactos
    if current.role_name == "secretary":
        return error_response("Secretaría solo puede ver contactos.", 403)

    contact = EmergencyContact.query.filter_by(id=contact_id, child_id=child_id).first()
    if not contact:
        return error_response("Contacto no encontrado.", 404)

    data = request.get_json(silent=True) or {}
    if "full_name" in data:
        contact.full_name = to_upper(data["full_name"])
    if "phone" in data:
        contact.phone = data["phone"]
    if "relationship" in data:
        contact.relationship = to_upper(data["relationship"])
    if "is_primary" in data and data["is_primary"]:
        EmergencyContact.query.filter_by(child_id=child_id, is_primary=True).update(
            {"is_primary": False}
        )
        contact.is_primary = True

    db.session.commit()
    return success_response(contact.to_dict(), "Contacto actualizado exitosamente.")


# ── DELETE /ninos/:id/contactos-emergencia/:cid ──────────────────────────────
@bp.route("/<int:contact_id>", methods=["DELETE"])
@any_authenticated
def delete_contact(child_id, contact_id):
    """Elimina un contacto. Valida que quede al menos 1."""
    current = get_current_user()
    child, err = _check_child_access(current, child_id, write=True)
    if err:
        return err

    if current.role_name == "secretary":
        return error_response("Secretaría no puede eliminar contactos.", 403)

    contact = EmergencyContact.query.filter_by(id=contact_id, child_id=child_id).first()
    if not contact:
        return error_response("Contacto no encontrado.", 404)

    total = EmergencyContact.query.filter_by(child_id=child_id).count()
    if total <= 1:
        return error_response("Debe quedar al menos 1 contacto de emergencia.", 400)

    db.session.delete(contact)
    db.session.commit()
    return success_response(message="Contacto eliminado exitosamente.")
