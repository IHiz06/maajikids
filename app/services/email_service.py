"""
MaajiKids — Servicio de Email (Flask-Mailman)
Todos los correos transaccionales del sistema.
"""
from flask import current_app
from flask_mailman import EmailMultiAlternatives
import logging

logger = logging.getLogger(__name__)


def _send(subject: str, to: str | list, body_plain: str, body_html: str | None = None) -> bool:
    """Envía email. Retorna True si OK, False si falla."""
    try:
        recipients = [to] if isinstance(to, str) else to
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_plain,
            from_email=current_app.config.get("MAIL_DEFAULT_SENDER"),
            to=recipients,
        )
        if body_html:
            msg.attach_alternative(body_html, "text/html")
        msg.send()
        return True
    except Exception as e:
        logger.error(f"[EmailService] Error enviando email a {to}: {e}")
        return False


# ── Templates ──────────────────────────────────────────────────────────────────
def send_verification_email(to_email: str, full_name: str, code: str) -> bool:
    """Código de verificación de cuenta."""
    subject = "MaajiKids — Verifica tu correo electrónico"
    plain = (
        f"Hola {full_name},\n\n"
        f"Tu código de verificación es: {code}\n\n"
        f"Este código expira en 24 horas.\n\n"
        f"Centro MaajiKids"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;">
      <h2 style="color:#E91E8C;">MaajiKids — Verifica tu cuenta</h2>
      <p>Hola <strong>{full_name}</strong>,</p>
      <p>Tu código de verificación es:</p>
      <div style="font-size:36px;font-weight:bold;letter-spacing:8px;
                  background:#f8f8f8;padding:16px 24px;border-radius:8px;
                  display:inline-block;margin:12px 0;">{code}</div>
      <p style="color:#888;font-size:13px;">Este código expira en 24 horas.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#aaa;font-size:12px;">Centro de Estimulación Temprana y Psicoprofilaxis MaajiKids</p>
    </div>
    """
    return _send(subject, to_email, plain, html)


def send_password_reset_email(to_email: str, full_name: str, code: str) -> bool:
    """Código de restablecimiento de contraseña."""
    subject = "MaajiKids — Restablecer contraseña"
    plain = (
        f"Hola {full_name},\n\n"
        f"Tu código para restablecer la contraseña es: {code}\n\n"
        f"Este código expira en 1 hora. Si no solicitaste este cambio, ignora este mensaje.\n\n"
        f"Centro MaajiKids"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;">
      <h2 style="color:#E91E8C;">MaajiKids — Restablecer contraseña</h2>
      <p>Hola <strong>{full_name}</strong>,</p>
      <p>Tu código para restablecer la contraseña es:</p>
      <div style="font-size:36px;font-weight:bold;letter-spacing:8px;
                  background:#f8f8f8;padding:16px 24px;border-radius:8px;
                  display:inline-block;margin:12px 0;">{code}</div>
      <p style="color:#888;font-size:13px;">Expira en 1 hora. Si no lo solicitaste, ignora este correo.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#aaa;font-size:12px;">Centro de Estimulación Temprana y Psicoprofilaxis MaajiKids</p>
    </div>
    """
    return _send(subject, to_email, plain, html)


def send_dni_pending_notification(admin_emails: list[str], child_name: str, parent_name: str) -> bool:
    """Notifica a admin/secretaría que un padre subió el DNI de su hijo."""
    subject = "MaajiKids — Documento DNI pendiente de revisión"
    plain = (
        f"Se ha subido un documento DNI pendiente de revisión.\n\n"
        f"Niño: {child_name}\n"
        f"Padre/Madre: {parent_name}\n\n"
        f"Ingresa al panel administrativo para revisar y verificar el documento."
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;">
      <h2 style="color:#E91E8C;">DNI Pendiente de Revisión</h2>
      <p>Se ha cargado un nuevo documento DNI que requiere tu revisión:</p>
      <ul>
        <li><strong>Niño/a:</strong> {child_name}</li>
        <li><strong>Padre/Madre:</strong> {parent_name}</li>
      </ul>
      <p>Ingresa al panel administrativo para verificar el documento.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#aaa;font-size:12px;">Centro de Estimulación Temprana y Psicoprofilaxis MaajiKids</p>
    </div>
    """
    return _send(subject, admin_emails, plain, html)


def send_dni_verified_email(to_email: str, parent_name: str, child_name: str) -> bool:
    """Notifica al padre que el DNI de su hijo fue verificado."""
    subject = "MaajiKids — DNI verificado exitosamente"
    plain = (
        f"Hola {parent_name},\n\n"
        f"El documento de identidad de {child_name} ha sido verificado correctamente.\n"
        f"Tu hijo/a ahora puede ser evaluado por los profesores del centro.\n\n"
        f"Centro MaajiKids"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;">
      <h2 style="color:#E91E8C;">✅ DNI Verificado</h2>
      <p>Hola <strong>{parent_name}</strong>,</p>
      <p>El documento de identidad de <strong>{child_name}</strong> ha sido
         <strong style="color:green;">verificado correctamente</strong>.</p>
      <p>Tu hijo/a ahora puede ser evaluado por los especialistas del centro.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#aaa;font-size:12px;">Centro de Estimulación Temprana y Psicoprofilaxis MaajiKids</p>
    </div>
    """
    return _send(subject, to_email, plain, html)


def send_payment_confirmation_email(to_email: str, parent_name: str,
                                    order_id: int, items: list[dict]) -> bool:
    """Confirmación de pago aprobado y activación de inscripciones."""
    subject = f"MaajiKids — Pago confirmado (Orden #{order_id})"
    items_text = "\n".join([f"  - {i['child_name']} → {i['workshop_title']}" for i in items])
    plain = (
        f"Hola {parent_name},\n\n"
        f"Tu pago para la Orden #{order_id} ha sido confirmado.\n\n"
        f"Inscripciones activadas:\n{items_text}\n\n"
        f"¡Gracias por confiar en MaajiKids!\n\nCentro MaajiKids"
    )
    items_html = "".join([
        f"<li><strong>{i['child_name']}</strong> → {i['workshop_title']}</li>"
        for i in items
    ])
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;">
      <h2 style="color:#E91E8C;">✅ Pago Confirmado — Orden #{order_id}</h2>
      <p>Hola <strong>{parent_name}</strong>,</p>
      <p>Tu pago ha sido procesado exitosamente. Las siguientes inscripciones están activas:</p>
      <ul>{items_html}</ul>
      <p>¡Gracias por confiar en <strong>MaajiKids</strong>! 🎉</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#aaa;font-size:12px;">Centro de Estimulación Temprana y Psicoprofilaxis MaajiKids</p>
    </div>
    """
    return _send(subject, to_email, plain, html)


def send_contact_reply_email(to_email: str, sender_name: str,
                             original_subject: str, reply_text: str) -> bool:
    """Envía respuesta al remitente de un mensaje de contacto."""
    subject = f"Re: {original_subject} — MaajiKids"
    plain = (
        f"Hola {sender_name},\n\n"
        f"Gracias por contactarnos. Aquí tienes nuestra respuesta:\n\n"
        f"{reply_text}\n\nCentro MaajiKids"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px;">
      <h2 style="color:#E91E8C;">Respuesta de MaajiKids</h2>
      <p>Hola <strong>{sender_name}</strong>, gracias por contactarnos.</p>
      <div style="background:#f9f9f9;border-left:4px solid #E91E8C;
                  padding:16px;border-radius:4px;margin:16px 0;">
        {reply_text.replace(chr(10), '<br>')}
      </div>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
      <p style="color:#aaa;font-size:12px;">Centro de Estimulación Temprana y Psicoprofilaxis MaajiKids</p>
    </div>
    """
    return _send(subject, to_email, plain, html)
