"""
MaajiKids — Blueprint: /talleres
5 endpoints. Imágenes opcionales vía Cloudinary (multipart/form-data).
GET es público. POST/PATCH/DELETE solo admin.
"""
from flask import Blueprint, request, send_file
from app.extensions import db
from app.models.workshop import Workshop
from app.models.user import User
from app.services.cloudinary_service import upload_workshop_image, delete_image_by_url
from app.utils.helpers import (
    to_upper, success_response, error_response,
    paginate_query, validate_image_file,
)
from app.utils.decorators import admin_required, any_authenticated, get_current_user
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError

bp = Blueprint("workshops", __name__, url_prefix="/talleres")


def _get_optional_user():
    """Intenta obtener el usuario autenticado sin lanzar error si no hay token."""
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            return db.session.get(User, int(uid))
    except Exception:
        pass
    return None


# ── GET /talleres/ ───────────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
def list_workshops():
    """
    Público. Params: ?asignados=true (teacher), ?activo=true|false, ?page=, ?per_page=
    Teacher con ?asignados=true ve solo sus talleres.
    """
    activo = request.args.get("activo")
    asignados = request.args.get("asignados", "").lower() == "true"
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    current_user = _get_optional_user()

    q = Workshop.query

    # Filtro por estado activo
    if activo is not None:
        q = q.filter(Workshop.is_active == (activo.lower() == "true"))

    # Si el usuario es teacher y pide sus talleres asignados
    if asignados and current_user and current_user.role_name == "teacher":
        q = q.filter(Workshop.teacher_id == current_user.id)

    q = q.order_by(Workshop.created_at.desc())
    result = paginate_query(q, page, per_page)
    result["items"] = [w.to_dict() for w in result["items"]]
    return success_response(result)


# ── GET /talleres/:id ────────────────────────────────────────────────────────
@bp.route("/<int:workshop_id>", methods=["GET"])
def get_workshop(workshop_id):
    """Detalle completo de un taller. Visible sin login."""
    ws = db.session.get(Workshop, workshop_id)
    if not ws:
        return error_response("Taller no encontrado.", 404)
    return success_response(ws.to_dict())


# ── POST /talleres/ ──────────────────────────────────────────────────────────
@bp.route("/", methods=["POST"])
@admin_required
def create_workshop():
    """
    Crea un nuevo taller. Acepta multipart/form-data.
    Campos: title, description, schedule, age_min, age_max,
            max_capacity, price, teacher_id (opcional), image (archivo opcional)
    """
    # Soporta tanto JSON como multipart
    if request.content_type and "multipart" in request.content_type:
        form = request.form
        image_file = request.files.get("image")
    else:
        form = request.get_json(silent=True) or {}
        image_file = None

    title = to_upper(form.get("title", ""))
    description = form.get("description", "")
    schedule = to_upper(form.get("schedule", ""))
    teacher_id = form.get("teacher_id")
    price = form.get("price")
    max_capacity = form.get("max_capacity")
    age_min = form.get("age_min")
    age_max = form.get("age_max")

    # Validaciones
    if not all([title, description, schedule, price, max_capacity, age_min, age_max]):
        return error_response(
            "Campos requeridos: title, description, schedule, price, max_capacity, age_min, age_max.", 400
        )
    try:
        price = float(price)
        max_capacity = int(max_capacity)
        age_min = int(age_min)
        age_max = int(age_max)
    except (ValueError, TypeError):
        return error_response("price, max_capacity, age_min, age_max deben ser numéricos.", 400)

    if age_min < 0 or age_max > 72 or age_min >= age_max:
        return error_response("Rango de edad inválido. age_min >= 0, age_max <= 72 (6 años), age_min < age_max.", 400)
    if price <= 0:
        return error_response("El precio debe ser mayor a 0.", 400)

    # Validar teacher_id si se provee
    if teacher_id:
        teacher = db.session.get(User, int(teacher_id))
        if not teacher or teacher.role_name not in ("teacher", "admin"):
            return error_response("El profesor asignado no existe o no tiene el rol correcto.", 400)

    ws = Workshop(
        title=title,
        description=description,
        schedule=schedule,
        teacher_id=int(teacher_id) if teacher_id else None,
        age_min=age_min,
        age_max=age_max,
        max_capacity=max_capacity,
        price=price,
        is_active=True,
    )
    db.session.add(ws)
    db.session.flush()  # Obtiene el ID antes de subir imagen

    # Subir imagen a Cloudinary si se envió
    if image_file and image_file.filename:
        valid, msg = validate_image_file(image_file)
        if not valid:
            db.session.rollback()
            return error_response(msg, 400)
        url = upload_workshop_image(image_file, ws.id)
        if url:
            ws.image_url = url

    db.session.commit()
    return success_response(ws.to_dict(), "Taller creado exitosamente.", 201)


# ── PATCH /talleres/:id ──────────────────────────────────────────────────────
@bp.route("/<int:workshop_id>", methods=["PATCH"])
@admin_required
def update_workshop(workshop_id):
    """Actualiza datos del taller. Si se envía imagen nueva, reemplaza la anterior en Cloudinary."""
    ws = db.session.get(Workshop, workshop_id)
    if not ws:
        return error_response("Taller no encontrado.", 404)

    if request.content_type and "multipart" in request.content_type:
        form = request.form
        image_file = request.files.get("image")
    else:
        form = request.get_json(silent=True) or {}
        image_file = None

    if "title" in form:
        ws.title = to_upper(form["title"])
    if "description" in form:
        ws.description = form["description"]
    if "schedule" in form:
        ws.schedule = to_upper(form["schedule"])
    if "teacher_id" in form:
        tid = form["teacher_id"]
        if tid:
            teacher = db.session.get(User, int(tid))
            if not teacher or teacher.role_name not in ("teacher", "admin"):
                return error_response("Profesor inválido.", 400)
            ws.teacher_id = int(tid)
        else:
            ws.teacher_id = None
    if "price" in form:
        try:
            ws.price = float(form["price"])
        except ValueError:
            return error_response("precio inválido.", 400)
    if "max_capacity" in form:
        try:
            ws.max_capacity = int(form["max_capacity"])
        except ValueError:
            return error_response("max_capacity inválido.", 400)
    if "age_min" in form:
        ws.age_min = int(form["age_min"])
    if "age_max" in form:
        ws.age_max = int(form["age_max"])
    if "is_active" in form:
        val = form["is_active"]
        ws.is_active = val if isinstance(val, bool) else val.lower() == "true"

    # Imagen nueva → elimina la anterior y sube la nueva
    if image_file and image_file.filename:
        valid, msg = validate_image_file(image_file)
        if not valid:
            return error_response(msg, 400)
        if ws.image_url:
            delete_image_by_url(ws.image_url)
        url = upload_workshop_image(image_file, ws.id)
        if url:
            ws.image_url = url

    db.session.commit()
    return success_response(ws.to_dict(), "Taller actualizado exitosamente.")


# ── DELETE /talleres/:id ─────────────────────────────────────────────────────
@bp.route("/<int:workshop_id>", methods=["DELETE"])
@admin_required
def delete_workshop(workshop_id):
    """Desactiva el taller (is_active=false)."""
    ws = db.session.get(Workshop, workshop_id)
    if not ws:
        return error_response("Taller no encontrado.", 404)

    ws.is_active = False
    db.session.commit()
    return success_response(message=f"Taller '{ws.title}' desactivado exitosamente.")
