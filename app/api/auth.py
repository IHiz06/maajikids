"""
MaajiKids — Blueprint: /autenticacion
8 endpoints de autenticación completos.
"""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
)
from app.extensions import db, limiter
from app.models.user import User
from app.models.role import Role
from app.models.token_blacklist import TokenBlacklist
from app.services.email_service import send_verification_email, send_password_reset_email
from app.utils.helpers import (
    normalize_email, to_upper, generate_verification_code,
    success_response, error_response, now_utc,
)
from app.utils.decorators import jwt_required_with_blacklist, get_current_user

bp = Blueprint("auth", __name__, url_prefix="/autenticacion")


# ── POST /autenticacion/registrar ─────────────────────────────────────────────
@bp.route("/registrar", methods=["POST"])
@limiter.limit("10 per minute")
def registrar():
    """Registro de nuevo usuario parent. Envía código de verificación al email."""
    data = request.get_json(silent=True) or {}

    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")
    first_name = to_upper(data.get("first_name", ""))
    last_name = to_upper(data.get("last_name", ""))
    phone = data.get("phone", "")

    # Validaciones básicas
    if not all([email, password, first_name, last_name]):
        return error_response("Campos requeridos: email, password, first_name, last_name.", 400)
    if len(password) < 8:
        return error_response("La contraseña debe tener al menos 8 caracteres.", 400)
    if "@" not in email:
        return error_response("Email inválido.", 400)
    if User.query.filter_by(email=email).first():
        return error_response("El email ya está registrado.", 409)

    # Rol parent por defecto
    parent_role = Role.query.filter_by(name="parent").first()
    if not parent_role:
        return error_response("Configuración del sistema incompleta. Contacta al administrador.", 500)

    code = generate_verification_code(6)
    expires = now_utc() + timedelta(hours=24)

    user = User(
        email=email,
        role_id=parent_role.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone or None,
        is_active=True,
        email_verified=False,
        verification_code=code,
        verification_expires=expires,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Envía email de verificación (no bloquea el registro si falla)
    send_verification_email(email, user.full_name, code)

    return success_response(
        {"user_id": user.id, "email": user.email},
        "Registro exitoso. Revisa tu email para verificar tu cuenta.",
        201,
    )


# ── POST /autenticacion/verificar-correo ─────────────────────────────────────
@bp.route("/verificar-correo", methods=["POST"])
@limiter.limit("10 per minute")
def verificar_correo():
    """Verifica el código enviado al email para activar la cuenta."""
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    code = data.get("codigo", "")

    if not email or not code:
        return error_response("Se requieren email y codigo.", 400)

    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response("Usuario no encontrado.", 404)
    if user.email_verified:
        return success_response(message="El correo ya fue verificado anteriormente.")
    if user.verification_code != code:
        return error_response("Código de verificación incorrecto.", 400)
    if user.verification_expires and user.verification_expires < now_utc():
        return error_response("El código ha expirado. Solicita uno nuevo.", 400)

    user.email_verified = True
    user.verification_code = None
    user.verification_expires = None
    db.session.commit()

    return success_response(message="Correo verificado exitosamente. Ahora puedes iniciar sesión.")


# ── POST /autenticacion/reenviar-verificacion ─────────────────────────────────
@bp.route("/reenviar-verificacion", methods=["POST"])
@limiter.limit("5 per minute")
def reenviar_verificacion():
    """Reenvía el código de verificación al email."""
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))

    if not email:
        return error_response("Se requiere el email.", 400)

    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response("Usuario no encontrado.", 404)
    if user.email_verified:
        return success_response(message="El correo ya fue verificado.")

    code = generate_verification_code(6)
    user.verification_code = code
    user.verification_expires = now_utc() + timedelta(hours=24)
    db.session.commit()

    send_verification_email(email, user.full_name, code)
    return success_response(message="Código de verificación reenviado. Revisa tu email.")


# ── POST /autenticacion/iniciar-sesion ───────────────────────────────────────
@bp.route("/iniciar-sesion", methods=["POST"])
@limiter.limit("10 per minute")
def iniciar_sesion():
    """Login. Retorna access_token (15 min) + refresh_token."""
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")

    if not email or not password:
        return error_response("Se requieren email y password.", 400)

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return error_response("Credenciales incorrectas.", 401)
    if not user.is_active:
        return error_response("Cuenta desactivada. Contacta al administrador.", 403)
    if not user.email_verified:
        return error_response("Debes verificar tu correo electrónico antes de iniciar sesión.", 403)

    user.last_login = now_utc()
    user.last_activity = now_utc()
    db.session.commit()

    identity = str(user.id)
    additional_claims = {"role": user.role_name, "email": user.email}
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)

    return success_response({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user": user.to_dict(),
    }, "Sesión iniciada exitosamente.")


# ── POST /autenticacion/renovar-token ────────────────────────────────────────
@bp.route("/renovar-token", methods=["POST"])
@jwt_required(refresh=True)
def renovar_token():
    """Genera nuevo access_token. Valida inactividad de 40 min."""
    jti = get_jwt().get("jti")
    # Verificar blacklist del refresh token
    if TokenBlacklist.query.filter_by(jti=jti).first():
        return error_response("Sesión expirada. Inicia sesión nuevamente.", 401)

    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user or not user.is_active:
        return error_response("Usuario no encontrado o desactivado.", 401)

    # Validar inactividad (40 min)
    if user.last_activity:
        inactive_since = now_utc() - user.last_activity
        if inactive_since > timedelta(minutes=40):
            return error_response(
                "Sesión expirada por inactividad. Inicia sesión nuevamente.", 401
            )

    user.last_activity = now_utc()
    db.session.commit()

    additional_claims = {"role": user.role_name, "email": user.email}
    new_access_token = create_access_token(
        identity=str(user.id), additional_claims=additional_claims
    )
    return success_response({
        "access_token": new_access_token,
        "token_type": "Bearer",
    }, "Token renovado exitosamente.")


# ── POST /autenticacion/cerrar-sesion ────────────────────────────────────────
@bp.route("/cerrar-sesion", methods=["POST"])
@jwt_required_with_blacklist
def cerrar_sesion():
    """Revoca el token actual insertando JTI en token_blacklist."""
    jwt_data = get_jwt()
    jti = jwt_data.get("jti")
    user_id = get_jwt_identity()
    exp = jwt_data.get("exp")

    expires_at = datetime.utcfromtimestamp(exp) if exp else now_utc()

    blacklist_entry = TokenBlacklist(
        jti=jti,
        token_type="access",
        user_id=int(user_id),
        expires_at=expires_at,
    )
    db.session.add(blacklist_entry)
    db.session.commit()

    return success_response(message="Sesión cerrada exitosamente.")


# ── POST /autenticacion/olvide-contrasena ────────────────────────────────────
@bp.route("/olvide-contrasena", methods=["POST"])
@limiter.limit("5 per minute")
def olvide_contrasena():
    """Envía email con código de restablecimiento de contraseña."""
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))

    if not email:
        return error_response("Se requiere el email.", 400)

    user = User.query.filter_by(email=email).first()
    # Siempre retornar 200 por seguridad (no revelar si el email existe)
    if user and user.is_active:
        code = generate_verification_code(6)
        user.verification_code = code
        user.verification_expires = now_utc() + timedelta(hours=1)
        db.session.commit()
        send_password_reset_email(email, user.full_name, code)

    return success_response(
        message="Si el correo está registrado, recibirás un código de restablecimiento."
    )


# ── POST /autenticacion/restablecer-contrasena ───────────────────────────────
@bp.route("/restablecer-contrasena", methods=["POST"])
@limiter.limit("10 per minute")
def restablecer_contrasena():
    """Restablece la contraseña usando el código recibido por email."""
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    code = data.get("codigo", "")
    new_password = data.get("nueva_password", "")

    if not all([email, code, new_password]):
        return error_response("Se requieren email, codigo y nueva_password.", 400)
    if len(new_password) < 8:
        return error_response("La contraseña debe tener al menos 8 caracteres.", 400)

    user = User.query.filter_by(email=email).first()
    if not user:
        return error_response("Datos inválidos.", 400)
    if user.verification_code != code:
        return error_response("Código incorrecto.", 400)
    if user.verification_expires and user.verification_expires < now_utc():
        return error_response("El código ha expirado.", 400)

    user.set_password(new_password)
    user.verification_code = None
    user.verification_expires = None
    db.session.commit()

    return success_response(message="Contraseña restablecida exitosamente. Ya puedes iniciar sesión.")
