"""
MaajiKids — Decoradores de autorización por rol

Arquitectura limpia de un solo nivel de wrapping:
  jwt_required_with_blacklist  → verifica token + blacklist
  roles_required(*roles)       → verifica token + blacklist + rol
  any_authenticated            → verifica token + blacklist + usuario activo
  Shortcuts (admin_required, etc.) → alias directos de roles_required
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request, get_jwt


def _get_db_and_models():
    """Import tardío para evitar imports circulares al cargar el módulo."""
    from app.extensions import db
    from app.models.user import User
    from app.models.token_blacklist import TokenBlacklist
    return db, User, TokenBlacklist


def _resolve_user():
    """Obtiene el User activo del JWT. Requiere contexto JWT activo."""
    db, User, _ = _get_db_and_models()
    uid = get_jwt_identity()
    if uid is None:
        return None
    return db.session.get(User, int(uid))


def _is_blacklisted(jti: str) -> bool:
    db, _, TokenBlacklist = _get_db_and_models()
    return db.session.query(TokenBlacklist).filter_by(jti=jti).first() is not None


# ── Decorador base: solo JWT + blacklist ─────────────────────────────────────
def jwt_required_with_blacklist(fn):
    """JWT required + verifica blacklist en PostgreSQL."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if _is_blacklisted(get_jwt().get("jti", "")):
            return jsonify({
                "success": False,
                "message": "Token revocado. Inicia sesión nuevamente.",
            }), 401
        return fn(*args, **kwargs)
    return wrapper


# ── Decorador principal de roles ─────────────────────────────────────────────
def roles_required(*allowed_roles: str):
    """
    Decorator factory. Verifica JWT, blacklist, cuenta activa y rol.
    Uso: @roles_required("admin", "secretary")
    """
    allowed = {r.lower() for r in allowed_roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 1. Verificar JWT
            try:
                verify_jwt_in_request()
            except Exception:
                return jsonify({"success": False, "message": "Token requerido."}), 401

            # 2. Verificar blacklist
            if _is_blacklisted(get_jwt().get("jti", "")):
                return jsonify({
                    "success": False,
                    "message": "Token revocado. Inicia sesión nuevamente.",
                }), 401

            # 3. Cargar usuario
            user = _resolve_user()
            if not user:
                return jsonify({"success": False, "message": "Usuario no encontrado."}), 404
            if not user.is_active:
                return jsonify({"success": False, "message": "Cuenta desactivada."}), 403

            # 4. Verificar rol
            if user.role_name not in allowed:
                return jsonify({
                    "success": False,
                    "message": "No tienes permisos para esta acción.",
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── any_authenticated: cualquier rol válido ──────────────────────────────────
def any_authenticated(fn):
    """Cualquier usuario autenticado (cualquier rol, activo)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({"success": False, "message": "Token requerido."}), 401

        if _is_blacklisted(get_jwt().get("jti", "")):
            return jsonify({
                "success": False,
                "message": "Token revocado. Inicia sesión nuevamente.",
            }), 401

        user = _resolve_user()
        if not user:
            return jsonify({"success": False, "message": "Usuario no encontrado."}), 404
        if not user.is_active:
            return jsonify({"success": False, "message": "Cuenta desactivada."}), 403
        return fn(*args, **kwargs)
    return wrapper


# ── Shortcuts ─────────────────────────────────────────────────────────────────
def admin_required(fn):
    """Solo admin."""
    return roles_required("admin")(fn)


def teacher_or_admin_required(fn):
    """Teacher o admin."""
    return roles_required("teacher", "admin")(fn)


def staff_required(fn):
    """Admin, teacher o secretary."""
    return roles_required("admin", "teacher", "secretary")(fn)


def parent_required(fn):
    """Solo parent."""
    return roles_required("parent")(fn)


# ── Helper de contexto ───────────────────────────────────────────────────────
def get_current_user():
    """
    Obtiene el User del JWT activo.
    Llamar SOLO dentro de endpoints con JWT verificado.
    Retorna None si no hay JWT o el usuario no existe.
    """
    try:
        return _resolve_user()
    except Exception:
        return None
