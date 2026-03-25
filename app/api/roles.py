"""
MaajiKids — Blueprint: /roles
5 endpoints de gestión de roles. Solo admin.
"""
from flask import Blueprint, request
from app.extensions import db
from app.models.role import Role
from app.utils.helpers import to_upper, success_response, error_response
from app.utils.decorators import admin_required, get_current_user

bp = Blueprint("roles", __name__, url_prefix="/roles")


# ── GET /roles/ ──────────────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
@admin_required
def list_roles():
    """Lista todos los roles (sistema + personalizados)."""
    roles = Role.query.order_by(Role.is_system.desc(), Role.name).all()
    return success_response([r.to_dict() for r in roles])


# ── POST /roles/ ─────────────────────────────────────────────────────────────
@bp.route("/", methods=["POST"])
@admin_required
def create_role():
    """Crea un rol personalizado con permisos JSONB."""
    data = request.get_json(silent=True) or {}
    name = to_upper(data.get("name", ""))
    description = data.get("description", "")
    permissions = data.get("permissions", {})

    if not name:
        return error_response("El nombre del rol es requerido.", 400)
    if Role.query.filter_by(name=name).first():
        return error_response("Ya existe un rol con ese nombre.", 409)
    if not isinstance(permissions, dict):
        return error_response("Los permisos deben ser un objeto JSON.", 400)

    current = get_current_user()
    role = Role(
        name=name,
        description=description,
        is_system=False,
        permissions=permissions,
        created_by=current.id if current else None,
    )
    db.session.add(role)
    db.session.commit()
    return success_response(role.to_dict(), "Rol creado exitosamente.", 201)


# ── GET /roles/:id ───────────────────────────────────────────────────────────
@bp.route("/<int:role_id>", methods=["GET"])
@admin_required
def get_role(role_id):
    """Detalle de un rol con sus permisos."""
    role = db.session.get(Role, role_id)
    if not role:
        return error_response("Rol no encontrado.", 404)
    return success_response(role.to_dict())


# ── PATCH /roles/:id ─────────────────────────────────────────────────────────
@bp.route("/<int:role_id>", methods=["PATCH"])
@admin_required
def update_role(role_id):
    """Actualiza nombre, descripción o permisos. No permite editar roles del sistema."""
    role = db.session.get(Role, role_id)
    if not role:
        return error_response("Rol no encontrado.", 404)
    if role.is_system:
        return error_response("No se pueden modificar los roles del sistema.", 403)

    data = request.get_json(silent=True) or {}
    if "name" in data:
        new_name = to_upper(data["name"])
        existing = Role.query.filter_by(name=new_name).first()
        if existing and existing.id != role_id:
            return error_response("Ya existe un rol con ese nombre.", 409)
        role.name = new_name
    if "description" in data:
        role.description = data["description"]
    if "permissions" in data:
        if not isinstance(data["permissions"], dict):
            return error_response("Los permisos deben ser un objeto JSON.", 400)
        role.permissions = data["permissions"]

    db.session.commit()
    return success_response(role.to_dict(), "Rol actualizado exitosamente.")


# ── DELETE /roles/:id ────────────────────────────────────────────────────────
@bp.route("/<int:role_id>", methods=["DELETE"])
@admin_required
def delete_role(role_id):
    """Elimina un rol personalizado. No permite eliminar roles del sistema."""
    role = db.session.get(Role, role_id)
    if not role:
        return error_response("Rol no encontrado.", 404)
    if role.is_system:
        return error_response("No se pueden eliminar los roles del sistema.", 403)

    # Verificar que no haya usuarios con este rol
    if role.users.count() > 0:
        return error_response(
            "No se puede eliminar: hay usuarios asignados a este rol. Reasígnalos primero.", 409
        )

    db.session.delete(role)
    db.session.commit()
    return success_response(message="Rol eliminado exitosamente.")
