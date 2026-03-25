"""
MaajiKids — Utilidades compartidas
"""
from __future__ import annotations
import re
import hashlib
import secrets
import string
from datetime import date, datetime, timezone
from typing import Any


# ── Texto MAYÚSCULAS (excepto email) ──────────────────────────────────────────
def to_upper(value: str | None) -> str | None:
    """Convierte texto a MAYÚSCULAS según regla del sistema."""
    if value is None:
        return None
    return value.strip().upper()


def normalize_email(email: str | None) -> str | None:
    """Email siempre en minúsculas (excepción a la regla de MAYÚSCULAS)."""
    if email is None:
        return None
    return email.strip().lower()


# ── Validaciones de edad ──────────────────────────────────────────────────────
def calculate_age_months(date_of_birth: date) -> int:
    """Calcula la edad en meses desde la fecha de nacimiento."""
    today = date.today()
    months = (today.year - date_of_birth.year) * 12 + (today.month - date_of_birth.month)
    if today.day < date_of_birth.day:
        months -= 1
    return max(0, months)


def validate_child_age(date_of_birth: date) -> tuple[bool, str]:
    """
    Valida que el niño tenga máximo 6 años (72 meses).
    Retorna (valid: bool, message: str).
    """
    months = calculate_age_months(date_of_birth)
    if months > 72:
        years = months // 12
        return False, f"La edad máxima para registrar un niño en MaajiKids es 6 años. El niño tiene {years} años."
    return True, ""


def child_fits_workshop_age(age_months: int, age_min: int, age_max: int) -> bool:
    """Verifica si la edad del niño está dentro del rango del taller."""
    return age_min <= age_months <= age_max


# ── Generadores de códigos ────────────────────────────────────────────────────
def generate_verification_code(length: int = 6) -> str:
    """Genera código numérico de verificación para email."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def generate_session_token() -> str:
    """Token aleatorio seguro para sesiones de chat anónimas."""
    return secrets.token_urlsafe(32)


def sha256_filename(original_name: str) -> str:
    """
    Genera nombre de archivo con hash SHA-256 para seguridad.
    Conserva la extensión original.
    """
    ext = original_name.rsplit(".", 1)[-1] if "." in original_name else ""
    random_bytes = secrets.token_bytes(32)
    h = hashlib.sha256(random_bytes).hexdigest()
    return f"{h}.{ext}" if ext else h


# ── Paginación ────────────────────────────────────────────────────────────────
def paginate_query(query, page: int = 1, per_page: int = 20) -> dict:
    """
    Aplica paginación a un query SQLAlchemy y retorna dict estándar.
    """
    page = max(1, int(page))
    per_page = min(100, max(1, int(per_page)))
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": paginated.items,
        "total": paginated.total,
        "page": paginated.page,
        "per_page": paginated.per_page,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
        "has_prev": paginated.has_prev,
    }


# ── Respuestas JSON estandarizadas ────────────────────────────────────────────
def success_response(data: Any = None, message: str = "OK", status_code: int = 200) -> tuple:
    """Respuesta de éxito estandarizada."""
    from flask import jsonify
    payload: dict = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def error_response(message: str, status_code: int = 400, errors: Any = None) -> tuple:
    """Respuesta de error estandarizada."""
    from flask import jsonify
    payload: dict = {"success": False, "message": message}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status_code


# ── Validación de archivos ────────────────────────────────────────────────────
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_DNI_MIME = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5 MB
MAX_DNI_SIZE = 5 * 1024 * 1024     # 5 MB


def validate_image_file(file) -> tuple[bool, str]:
    """Valida que el archivo sea imagen válida y no exceda 5MB."""
    if file.content_type not in ALLOWED_IMAGE_MIME:
        return False, "Tipo de archivo no permitido. Use JPEG, PNG o WEBP."
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_IMAGE_SIZE:
        return False, "La imagen no puede superar los 5MB."
    return True, ""


def validate_dni_file(file) -> tuple[bool, str]:
    """Valida que el archivo DNI sea imagen o PDF y no exceda 5MB."""
    if file.content_type not in ALLOWED_DNI_MIME:
        return False, "Tipo de archivo no permitido. Use JPEG, PNG, WEBP o PDF."
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_DNI_SIZE:
        return False, "El documento no puede superar los 5MB."
    return True, ""


# ── Utilidad de fechas ────────────────────────────────────────────────────────
def now_utc() -> datetime:
    """
    Retorna datetime UTC naive.
    Compatible con SQLite (tests) y PostgreSQL (producción).
    PostgreSQL trata los timestamps sin tz como UTC por defecto.
    """
    return datetime.utcnow()


def parse_date(date_str: str) -> date | None:
    """Parsea string YYYY-MM-DD a objeto date. Retorna None si falla."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
