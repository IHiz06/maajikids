"""
MaajiKids — Cifrado AES-256 con Fernet
Usado para datos médicos sensibles de los niños (medical_info, allergies).
"""
import os
from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.environ.get("FERNET_KEY", "")
    if not key:
        # En desarrollo sin clave, genera una temporal (no persistente)
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_text(text: str | None) -> str | None:
    """Cifra texto plano con Fernet/AES-256. Retorna None si input es None."""
    if text is None or text.strip() == "":
        return None
    f = _get_fernet()
    return f.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str | None) -> str | None:
    """Descifra token Fernet. Retorna None si falla o si input es None."""
    if token is None:
        return None
    try:
        f = _get_fernet()
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return None
