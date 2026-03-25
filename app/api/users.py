"""
MaajiKids — Blueprint: /usuarios
6 endpoints de gestión de usuarios.
"""
from flask import Blueprint, request
from app.extensions import db
from app.models.user import User
from app.models.role import Role
from app.utils.helpers import (
    normalize_email, to_upper, success_response, error_response, paginate_query
)
from app.utils.decorators import admin_required, any_authenticated, get_current_user

bp = Blueprint("users", __name__, url_prefix="/usuarios")


# ── GET /usuarios/ ───────────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
@admin_required
def list_users():
    """Lista todos los usuarios (admin). ?rol= ?page= ?per_page="""
    rol = request.args.get("rol")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    q = User.query
    if rol:
        q = q.join(Role).filter(Role.name == rol.lower())
    q = q.order_by(User.created_at.desc())

    result = paginate_query(q, page, per_page)
    result["items"] = [u.to_dict() for u in result["items"]]
    return success_response(result)


# ── POST /usuarios/ ──────────────────────────────────────────────────────────
@bp.route("/", methods=["POST"])
@admin_required
def create_user():
    """Admin crea usuario con cualquier rol."""
    data = request.get_json(silent=True) or {}

    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")
    first_name = to_upper(data.get("first_name", ""))
    last_name = to_upper(data.get("last_name", ""))
    phone = data.get("phone")
    role_id = data.get("role_id")

    if not all([email, password, first_name, last_name, role_id]):
        return error_response("Campos requeridos: email, password, first_name, last_name, role_id.", 400)
    if len(password) < 8:
        return error_response("La contraseña debe tener al menos 8 caracteres.", 400)
    if User.query.filter_by(email=email).first():
        return error_response("El email ya está registrado.", 409)

    role = db.session.get(Role, int(role_id))
    if not role:
        return error_response("Rol no encontrado.", 404)

    user = User(
        email=email,
        role_id=role.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        is_active=True,
        email_verified=True,  # Admin crea usuarios ya verificados
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return success_response(user.to_dict(), "Usuario creado exitosamente.", 201)


# ── GET /usuarios/yo ─────────────────────────────────────────────────────────
@bp.route("/yo", methods=["GET"])
@any_authenticated
def get_me():
    """Perfil del usuario autenticado actual."""
    user = get_current_user()
    if not user:
        return error_response("Usuario no encontrado.", 404)
    return success_response(user.to_dict())


# ── GET /usuarios/:id ────────────────────────────────────────────────────────
@bp.route("/<int:user_id>", methods=["GET"])
@any_authenticated
def get_user(user_id):
    """Detalle de usuario. Parent solo puede ver su propio perfil."""
    current = get_current_user()
    if not current:
        return error_response("No autenticado.", 401)

    if current.role_name != "admin" and current.id != user_id:
        return error_response("No tienes permisos para ver este perfil.", 403)

    user = db.session.get(User, user_id)
    if not user:
        return error_response("Usuario no encontrado.", 404)

    return success_response(user.to_dict())


# ── PATCH /usuarios/:id ──────────────────────────────────────────────────────
@bp.route("/<int:user_id>", methods=["PATCH"])
@any_authenticated
def update_user(user_id):
    """Actualiza datos del usuario. Admin puede cambiar rol."""
    current = get_current_user()
    if not current:
        return error_response("No autenticado.", 401)

    is_admin = current.role_name == "admin"
    if not is_admin and current.id != user_id:
        return error_response("No tienes permisos para editar este usuario.", 403)

    user = db.session.get(User, user_id)
    if not user:
        return error_response("Usuario no encontrado.", 404)

    data = request.get_json(silent=True) or {}

    if "first_name" in data:
        user.first_name = to_upper(data["first_name"])
    if "last_name" in data:
        user.last_name = to_upper(data["last_name"])
    if "phone" in data:
        user.phone = data["phone"] or None
    if "password" in data:
        pwd = data["password"]
        if len(pwd) < 8:
            return error_response("La contraseña debe tener al menos 8 caracteres.", 400)
        user.set_password(pwd)

    # Solo admin puede cambiar rol e is_active
    if is_admin:
        if "role_id" in data:
            role = db.session.get(Role, int(data["role_id"]))
            if not role:
                return error_response("Rol no encontrado.", 404)
            user.role_id = role.id
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

    db.session.commit()
    return success_response(user.to_dict(), "Usuario actualizado exitosamente.")


# ── DELETE /usuarios/:id ─────────────────────────────────────────────────────
@bp.route("/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """Desactiva usuario (is_active=false). No elimina físicamente."""
    current = get_current_user()
    if current and current.id == user_id:
        return error_response("No puedes desactivar tu propia cuenta.", 400)

    user = db.session.get(User, user_id)
    if not user:
        return error_response("Usuario no encontrado.", 404)

    user.is_active = False
    db.session.commit()
    return success_response(message=f"Usuario {user.full_name} desactivado exitosamente.")
