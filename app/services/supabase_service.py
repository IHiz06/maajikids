"""
MaajiKids — Servicio Supabase Storage
Almacenamiento privado de documentos DNI.

FIXES v5.1:
  - Respuesta de create_signed_url es objeto con .signed_url (no dict en supabase-py 2.x)
  - Mejor diagnóstico de errores (muestra el error real)
  - Validación de credenciales antes de intentar subir
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)

BUCKET_NAME = "dni-documents"


def _get_client():
    from supabase import create_client
    url = current_app.config.get("SUPABASE_URL", "").strip()
    key = current_app.config.get("SUPABASE_SERVICE_KEY", "").strip()
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL y SUPABASE_SERVICE_KEY no están configurados en .env"
        )
    return create_client(url, key)


def _extract_signed_url(signed_response) -> str | None:
    """Soporta supabase-py 1.x (dict) y 2.x (objeto)."""
    if signed_response is None:
        return None
    if hasattr(signed_response, "signed_url"):
        return signed_response.signed_url
    if isinstance(signed_response, dict):
        return (
            signed_response.get("signedURL")
            or signed_response.get("signedUrl")
            or signed_response.get("signed_url")
        )
    if isinstance(signed_response, str):
        return signed_response
    return None


def upload_dni_document(file_bytes: bytes, filename: str, content_type: str) -> str | None:
    """Sube DNI y retorna URL firmada (1 año) o None si falla."""
    try:
        client = _get_client()
        path = f"documentos/{filename}"

        client.storage.from_(BUCKET_NAME).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        logger.info(f"[Supabase] Subido: {path}")

        signed_response = client.storage.from_(BUCKET_NAME).create_signed_url(
            path=path, expires_in=31536000
        )
        url = _extract_signed_url(signed_response)

        if not url:
            # Fallback a URL pública si el bucket lo permite
            base = current_app.config.get("SUPABASE_URL", "")
            url = f"{base}/storage/v1/object/public/{BUCKET_NAME}/{path}"
            logger.warning(f"[Supabase] Signed URL vacía, usando fallback: {url[:60]}")

        return url

    except ValueError as e:
        logger.error(f"[Supabase] Configuración incompleta: {e}")
        raise
    except Exception as e:
        logger.error(f"[Supabase] Error subiendo '{filename}': {type(e).__name__}: {e}")
        return None


def delete_dni_document(filename: str) -> bool:
    try:
        client = _get_client()
        client.storage.from_(BUCKET_NAME).remove([f"documentos/{filename}"])
        return True
    except Exception as e:
        logger.error(f"[Supabase] Error eliminando '{filename}': {e}")
        return False


def get_signed_url(path_in_bucket: str, expires_in: int = 3600) -> str | None:
    try:
        client = _get_client()
        r = client.storage.from_(BUCKET_NAME).create_signed_url(
            path=path_in_bucket, expires_in=expires_in
        )
        return _extract_signed_url(r)
    except Exception as e:
        logger.error(f"[Supabase] Error generando signed URL: {e}")
        return None


def check_bucket_exists() -> bool:
    """Diagnóstico: verifica que el bucket existe."""
    try:
        client = _get_client()
        buckets = client.storage.list_buckets()
        names = [b.name if hasattr(b, "name") else b.get("name", "") for b in buckets]
        exists = BUCKET_NAME in names
        if not exists:
            logger.warning(
                f"[Supabase] Bucket '{BUCKET_NAME}' NO encontrado. "
                f"Disponibles: {names}. Créalo en Supabase → Storage → New bucket → privado."
            )
        return exists
    except Exception as e:
        logger.error(f"[Supabase] Error verificando buckets: {e}")
        return False
