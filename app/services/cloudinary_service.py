"""
MaajiKids — Servicio Cloudinary
Subida, actualización y eliminación de imágenes (talleres y fotos de niños).
"""
import os
import logging
import cloudinary
import cloudinary.uploader
from flask import current_app

logger = logging.getLogger(__name__)


def _configure():
    cloudinary.config(
        cloud_name=current_app.config.get("CLOUDINARY_CLOUD_NAME"),
        api_key=current_app.config.get("CLOUDINARY_API_KEY"),
        api_secret=current_app.config.get("CLOUDINARY_API_SECRET"),
        secure=True,
    )


def upload_workshop_image(file, workshop_id: int) -> str | None:
    """
    Sube imagen de taller a Cloudinary.
    Retorna URL segura o None si falla.
    """
    try:
        _configure()
        result = cloudinary.uploader.upload(
            file,
            folder="maajikids/talleres",
            public_id=f"taller_{workshop_id}",
            overwrite=True,
            resource_type="image",
            allowed_formats=["jpg", "jpeg", "png", "webp"],
            transformation=[
                {"width": 800, "height": 600, "crop": "fill", "quality": "auto"},
            ],
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"[Cloudinary] Error subiendo imagen de taller {workshop_id}: {e}")
        return None


def upload_child_photo(file, child_id: int) -> str | None:
    """
    Sube foto de niño a Cloudinary.
    Retorna URL segura o None si falla.
    """
    try:
        _configure()
        result = cloudinary.uploader.upload(
            file,
            folder="maajikids/ninos",
            public_id=f"nino_{child_id}",
            overwrite=True,
            resource_type="image",
            allowed_formats=["jpg", "jpeg", "png", "webp"],
            transformation=[
                {"width": 400, "height": 400, "crop": "fill", "gravity": "face", "quality": "auto"},
            ],
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"[Cloudinary] Error subiendo foto de niño {child_id}: {e}")
        return None


def delete_image_by_url(image_url: str) -> bool:
    """
    Elimina imagen en Cloudinary a partir de su URL pública.
    Retorna True si OK.
    """
    try:
        _configure()
        # Extrae public_id de la URL
        # URL format: https://res.cloudinary.com/cloud/image/upload/vXXX/folder/public_id.ext
        parts = image_url.split("/upload/")
        if len(parts) < 2:
            return False
        public_id_with_ext = parts[1].split("/", 1)[-1]  # quita versión
        public_id = public_id_with_ext.rsplit(".", 1)[0]  # quita extensión
        cloudinary.uploader.destroy(public_id, resource_type="image")
        return True
    except Exception as e:
        logger.error(f"[Cloudinary] Error eliminando imagen {image_url}: {e}")
        return False
