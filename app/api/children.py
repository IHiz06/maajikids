"""
MaajiKids — Blueprint: /ninos
7 endpoints. Cifrado AES-256 de datos médicos. DNI en Supabase Storage.
Foto del niño en Cloudinary.

FIXES v5.1:
  - DNI: acepta campo 'dni', 'file', 'document' (flexibilidad frontend)
  - DNI: error claro si Supabase no está configurado (no falla silenciosamente)
  - DNI: loguea el error real de Supabase
  - Mejorada validación de content_type para archivos sin MIME declarado
"""
import logging
from datetime import datetime, timezone
from flask import Blueprint, request
from app.extensions import db
from app.models.child import Child
from app.models.user import User
from app.models.enrollment import Enrollment
from app.services.cloudinary_service import upload_child_photo, delete_image_by_url
from app.services.email_service import send_dni_pending_notification, send_dni_verified_email
from app.utils.crypto import encrypt_text, decrypt_text
from app.utils.helpers import (
    to_upper, success_response, error_response, paginate_query,
    validate_image_file, validate_dni_file, sha256_filename,
    validate_child_age, now_utc,
)
from app.utils.decorators import any_authenticated, get_current_user

bp = Blueprint("children", __name__, url_prefix="/ninos")
logger = logging.getLogger(__name__)


def _can_access_child(current_user: User, child: Child) -> bool:
    role = current_user.role_name
    if role in ("admin", "secretary"):
        return True
    if role == "parent" and child.parent_id == current_user.id:
        return True
    if role == "teacher":
        from app.models.workshop import Workshop
        teacher_ws_ids = {ws.id for ws in Workshop.query.filter_by(teacher_id=current_user.id).all()}
        enrolled_ws_ids = {e.workshop_id for e in child.enrollments.filter_by(status="active")}
        return bool(teacher_ws_ids & enrolled_ws_ids)
    return False


# ── GET /ninos/ ──────────────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
@any_authenticated
def list_children():
    current = get_current_user()
    role = current.role_name
    taller_id = request.args.get("taller_id", type=int)
    dni_pendiente = request.args.get("dni_pendiente", "").lower() == "true"
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    q = Child.query.filter_by(is_active=True)

    if role == "parent":
        q = q.filter_by(parent_id=current.id)
    elif role == "teacher":
        from app.models.workshop import Workshop
        teacher_ws_ids = [ws.id for ws in Workshop.query.filter_by(teacher_id=current.id).all()]
        if taller_id:
            if taller_id not in teacher_ws_ids:
                return error_response("No tienes acceso a ese taller.", 403)
            teacher_ws_ids = [taller_id]
        child_ids = [
            c[0] for c in db.session.query(Enrollment.child_id)
            .filter(Enrollment.workshop_id.in_(teacher_ws_ids), Enrollment.status == "active")
            .distinct().all()
        ]
        q = q.filter(Child.id.in_(child_ids))
    elif role in ("admin", "secretary"):
        if taller_id:
            child_ids = [
                c[0] for c in db.session.query(Enrollment.child_id)
                .filter(Enrollment.workshop_id == taller_id, Enrollment.status == "active")
                .distinct().all()
            ]
            q = q.filter(Child.id.in_(child_ids))
        if dni_pendiente:
            q = q.filter_by(dni_pending_review=True)
    else:
        return error_response("Sin permisos.", 403)

    q = q.order_by(Child.full_name)
    result = paginate_query(q, page, per_page)
    result["items"] = [c.to_dict() for c in result["items"]]
    return success_response(result)


# ── POST /ninos/ ─────────────────────────────────────────────────────────────
@bp.route("/", methods=["POST"])
@any_authenticated
def create_child():
    from app.models.emergency_contact import EmergencyContact
    from app.utils.helpers import parse_date

    current = get_current_user()
    role = current.role_name

    if role not in ("parent", "admin", "secretary"):
        return error_response("No tienes permisos para registrar niños.", 403)

    if request.content_type and "multipart" in request.content_type:
        form = request.form
        photo_file = request.files.get("photo")
    else:
        form = request.get_json(silent=True) or {}
        photo_file = None

    full_name = to_upper(form.get("full_name", ""))
    dob_str = form.get("date_of_birth", "")
    gender = (form.get("gender") or "").upper()
    medical_info = form.get("medical_info", "")
    allergies = form.get("allergies", "")

    if role in ("admin", "secretary"):
        parent_id = form.get("parent_id")
        if not parent_id:
            return error_response("admin/secretary debe especificar parent_id.", 400)
        parent_id = int(parent_id)
        parent_user = db.session.get(User, parent_id)
        if not parent_user:
            return error_response("Padre no encontrado.", 404)
    else:
        parent_id = current.id
        parent_user = current

    if not full_name or not dob_str or not gender:
        return error_response("Campos requeridos: full_name, date_of_birth, gender.", 400)
    if gender not in ("M", "F", "OTRO"):
        return error_response("gender debe ser M, F u OTRO.", 400)

    dob = parse_date(dob_str)
    if not dob:
        return error_response("date_of_birth debe tener formato YYYY-MM-DD.", 400)

    valid_age, age_msg = validate_child_age(dob)
    if not valid_age:
        return error_response(age_msg, 400)

    child = Child(
        parent_id=parent_id,
        full_name=full_name,
        date_of_birth=dob,
        gender=gender,
        medical_info=encrypt_text(medical_info) if medical_info else None,
        allergies=encrypt_text(allergies) if allergies else None,
        payment_status="none",
    )
    db.session.add(child)
    db.session.flush()

    if photo_file and photo_file.filename:
        valid, msg = validate_image_file(photo_file)
        if not valid:
            db.session.rollback()
            return error_response(msg, 400)
        url = upload_child_photo(photo_file, child.id)
        if url:
            child.photo_url = url

    emergency = EmergencyContact(
        child_id=child.id,
        full_name=parent_user.full_name,
        phone=parent_user.phone or "",
        relationship="PADRE/MADRE",
        is_primary=True,
        order_index=1,
    )
    db.session.add(emergency)
    db.session.commit()

    return success_response(child.to_dict(), "Niño registrado exitosamente.", 201)


# ── GET /ninos/:id ───────────────────────────────────────────────────────────
@bp.route("/<int:child_id>", methods=["GET"])
@any_authenticated
def get_child(child_id):
    current = get_current_user()
    child = db.session.get(Child, child_id)
    if not child or not child.is_active:
        return error_response("Niño no encontrado.", 404)
    if not _can_access_child(current, child):
        return error_response("No tienes permisos para ver este niño.", 403)

    data = child.to_dict(include_medical=True)
    if data.get("medical_info"):
        data["medical_info"] = decrypt_text(data["medical_info"])
    if data.get("allergies"):
        data["allergies"] = decrypt_text(data["allergies"])
    return success_response(data)


# ── PATCH /ninos/:id ─────────────────────────────────────────────────────────
@bp.route("/<int:child_id>", methods=["PATCH"])
@any_authenticated
def update_child(child_id):
    from app.utils.helpers import parse_date
    current = get_current_user()
    child = db.session.get(Child, child_id)
    if not child or not child.is_active:
        return error_response("Niño no encontrado.", 404)

    role = current.role_name
    if role == "parent" and child.parent_id != current.id:
        return error_response("No tienes permisos para editar este niño.", 403)
    if role not in ("parent", "admin", "secretary"):
        return error_response("No tienes permisos para editar niños.", 403)

    if request.content_type and "multipart" in request.content_type:
        form = request.form
        photo_file = request.files.get("photo")
    else:
        form = request.get_json(silent=True) or {}
        photo_file = None

    if "full_name" in form:
        child.full_name = to_upper(form["full_name"])
    if "date_of_birth" in form:
        dob = parse_date(form["date_of_birth"])
        if not dob:
            return error_response("date_of_birth inválido.", 400)
        valid_age, age_msg = validate_child_age(dob)
        if not valid_age:
            return error_response(age_msg, 400)
        child.date_of_birth = dob
    if "gender" in form:
        g = form["gender"].upper()
        if g not in ("M", "F", "OTRO"):
            return error_response("gender debe ser M, F u OTRO.", 400)
        child.gender = g
    if "medical_info" in form:
        child.medical_info = encrypt_text(form["medical_info"]) if form["medical_info"] else None
    if "allergies" in form:
        child.allergies = encrypt_text(form["allergies"]) if form["allergies"] else None

    if photo_file and photo_file.filename:
        valid, msg = validate_image_file(photo_file)
        if not valid:
            return error_response(msg, 400)
        if child.photo_url:
            delete_image_by_url(child.photo_url)
        url = upload_child_photo(photo_file, child.id)
        if url:
            child.photo_url = url

    db.session.commit()
    return success_response(child.to_dict(), "Datos del niño actualizados exitosamente.")


# ── DELETE /ninos/:id ────────────────────────────────────────────────────────
@bp.route("/<int:child_id>", methods=["DELETE"])
@any_authenticated
def delete_child(child_id):
    current = get_current_user()
    if current.role_name != "admin":
        return error_response("Solo el administrador puede desactivar niños.", 403)
    child = db.session.get(Child, child_id)
    if not child:
        return error_response("Niño no encontrado.", 404)
    child.is_active = False
    db.session.commit()
    return success_response(message=f"Niño '{child.full_name}' desactivado exitosamente.")


# ── POST /ninos/:id/dni ──────────────────────────────────────────────────────
@bp.route("/<int:child_id>/dni", methods=["POST"])
@any_authenticated
def upload_dni(child_id):
    """
    Sube copia del DNI del niño a Supabase Storage.
    Acepta el archivo en el campo: 'dni', 'file' o 'document'.
    Activa dni_pending_review=True y notifica a admin/secretaría.

    IMPORTANTE: Requiere SUPABASE_URL y SUPABASE_SERVICE_KEY en .env
    y el bucket 'dni-documents' creado como PRIVADO en Supabase Storage.
    """
    from app.services.supabase_service import upload_dni_document, check_bucket_exists

    current = get_current_user()
    child = db.session.get(Child, child_id)
    if not child or not child.is_active:
        return error_response("Niño no encontrado.", 404)

    role = current.role_name
    if role == "parent" and child.parent_id != current.id:
        return error_response("No puedes subir DNI de otro padre.", 403)
    if role not in ("parent", "admin", "secretary"):
        return error_response("Sin permisos para subir DNI.", 403)

    # Acepta campo 'dni', 'file' o 'document' (flexibilidad de frontend)
    dni_file = (
        request.files.get("dni")
        or request.files.get("file")
        or request.files.get("document")
    )
    if not dni_file or not dni_file.filename:
        return error_response(
            "Se requiere el archivo DNI. "
            "Envía el campo 'dni' (o 'file'/'document') en el form-data.", 400
        )

    # Si el navegador no declara content_type, intentar inferirlo por extensión
    ct = dni_file.content_type or ""
    if not ct or ct == "application/octet-stream":
        ext = dni_file.filename.rsplit(".", 1)[-1].lower() if "." in dni_file.filename else ""
        ct = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp",
            "pdf": "application/pdf",
        }.get(ext, "application/octet-stream")
        dni_file.content_type = ct

    valid, msg = validate_dni_file(dni_file)
    if not valid:
        return error_response(msg, 400)

    safe_name = sha256_filename(dni_file.filename)
    file_bytes = dni_file.read()
    content_type = dni_file.content_type

    try:
        url = upload_dni_document(file_bytes, safe_name, content_type)
    except ValueError as e:
        # Supabase no configurado
        return error_response(
            f"Supabase Storage no configurado: {str(e)}. "
            f"Agrega SUPABASE_URL y SUPABASE_SERVICE_KEY en tu archivo .env.", 500
        )

    if not url:
        return error_response(
            "Error al subir el documento a Supabase Storage. "
            "Verifica que el bucket 'dni-documents' existe y que las credenciales son correctas. "
            "Revisa los logs del servidor para más detalles.", 500
        )

    child.dni_document_url = url
    child.dni_uploaded_by = role
    child.dni_pending_review = True
    child.dni_verified = False
    db.session.commit()
    logger.info(f"[DNI] Subido para niño {child_id} por {role} ({current.email})")

    # Notificar a admin y secretaría
    try:
        from app.models.role import Role
        admin_role = Role.query.filter_by(name="admin").first()
        sec_role = Role.query.filter_by(name="secretary").first()
        admin_emails = []
        if admin_role:
            admin_emails += [u.email for u in User.query.filter_by(role_id=admin_role.id, is_active=True).all()]
        if sec_role:
            admin_emails += [u.email for u in User.query.filter_by(role_id=sec_role.id, is_active=True).all()]
        if admin_emails:
            send_dni_pending_notification(admin_emails, child.full_name, current.full_name)
    except Exception as e:
        logger.warning(f"[DNI] No se pudo enviar notificación por email: {e}")

    return success_response(
        {
            "dni_document_url": url,
            "dni_pending_review": True,
            "dni_verified": False,
            "mensaje": "DNI subido exitosamente. Pendiente de revisión por admin/secretaría.",
        },
        "DNI subido exitosamente. El equipo revisará el documento.",
        201,
    )


# ── PATCH /ninos/:id/dni ─────────────────────────────────────────────────────
@bp.route("/<int:child_id>/dni", methods=["PATCH"])
@any_authenticated
def verify_dni(child_id):
    """
    Admin o secretaría confirma (o rechaza) la verificación de identidad.
    Body: {"dni_verified": true}   → aprueba
    Body: {"dni_verified": false}  → rechaza
    """
    current = get_current_user()
    if current.role_name not in ("admin", "secretary"):
        return error_response("Solo admin o secretaría pueden verificar DNI.", 403)

    child = db.session.get(Child, child_id)
    if not child or not child.is_active:
        return error_response("Niño no encontrado.", 404)
    if not child.dni_document_url:
        return error_response(
            "El niño no tiene documento DNI subido. "
            "El padre debe subirlo primero usando POST /ninos/:id/dni.", 400
        )

    data = request.get_json(silent=True) or {}
    verified = bool(data.get("dni_verified", True))

    child.dni_verified = verified
    child.dni_pending_review = False
    db.session.commit()

    if verified:
        parent = db.session.get(User, child.parent_id)
        if parent:
            try:
                send_dni_verified_email(parent.email, parent.full_name, child.full_name)
            except Exception as e:
                logger.warning(f"[DNI] No se pudo enviar email de verificación: {e}")

    status_msg = "DNI verificado exitosamente. El niño puede ser evaluado." if verified else "DNI rechazado. El padre debe subir un documento válido."
    return success_response(
        {
            "dni_verified": child.dni_verified,
            "dni_pending_review": child.dni_pending_review,
            "child_id": child.id,
        },
        status_msg,
    )
