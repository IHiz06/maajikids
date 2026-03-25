"""
MaajiKids — Blueprint: /pagos
3 endpoints. Sin webhook. Verificación activa con API de MercadoPago.

FIXES v5.1:
  - SDK MercadoPago v2: acepta status 200 Y 201
  - Loguea la respuesta COMPLETA de MP para debug
  - Permite a admin verificar pagos (no solo parent)
  - Endpoint GET /pagos/verificar-debug para diagnóstico (solo admin)
  - Manejo correcto de UniqueConstraint en Enrollments (no crash si ya existe)
"""
import logging
from datetime import datetime
from flask import Blueprint, request, current_app
from app.extensions import db, limiter
from app.models.order import Order, OrderItem
from app.models.child import Child
from app.models.workshop import Workshop
from app.models.enrollment import Enrollment
from app.services.email_service import send_payment_confirmation_email
from app.utils.helpers import success_response, error_response, paginate_query, now_utc, parse_date
from app.utils.decorators import any_authenticated, get_current_user
import mercadopago

bp = Blueprint("payments", __name__, url_prefix="/pagos")
logger = logging.getLogger(__name__)


def _mp_sdk():
    token = current_app.config.get("MP_ACCESS_TOKEN", "")
    if not token:
        raise ValueError("MP_ACCESS_TOKEN no configurado en .env")
    return mercadopago.SDK(token)


def _process_approved_payment(order: Order, payment_id, current_user) -> dict:
    """
    Procesa un pago aprobado: crea enrollments, actualiza estados.
    Retorna dict con los items enrollados.
    """
    order.status = "approved"
    order.mp_payment_id = str(payment_id)
    order.paid_at = now_utc()

    enrolled_items = []
    for item in order.items:
        # Crear enrollment si no existe (idempotente)
        existing = Enrollment.query.filter_by(
            child_id=item.child_id,
            workshop_id=item.workshop_id,
        ).first()

        if not existing:
            enroll = Enrollment(
                child_id=item.child_id,
                workshop_id=item.workshop_id,
                order_id=order.id,
                status="active",
            )
            db.session.add(enroll)
            ws = db.session.get(Workshop, item.workshop_id)
            if ws:
                ws.current_enrolled = ws.current_enrolled + 1
        elif existing.status == "cancelled":
            existing.status = "active"

        child = db.session.get(Child, item.child_id)
        if child:
            child.payment_status = "verified"

        enrolled_items.append({
            "child_name": item.child.full_name if item.child else f"Niño #{item.child_id}",
            "workshop_title": item.workshop.title if item.workshop else f"Taller #{item.workshop_id}",
        })

    db.session.commit()
    logger.info(f"[Pago] Orden #{order.id} APROBADA. Enrollments: {enrolled_items}")

    try:
        send_payment_confirmation_email(
            current_user.email, current_user.full_name, order.id, enrolled_items
        )
    except Exception as e:
        logger.warning(f"[Pago] Email de confirmación no enviado: {e}")

    return enrolled_items


# ── GET /pagos/ ───────────────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
@any_authenticated
def list_payments():
    """Historial de pagos. Parent ve los suyos, admin/secretary ven todos."""
    current = get_current_user()
    role = current.role_name
    estado = request.args.get("estado")
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    if role not in ("parent", "admin", "secretary"):
        return error_response("Sin permisos.", 403)

    q = Order.query
    if role == "parent":
        q = q.filter_by(parent_id=current.id)

    if estado:
        q = q.filter_by(status=estado)
    if desde:
        d = parse_date(desde)
        if d:
            q = q.filter(Order.created_at >= d)
    if hasta:
        h = parse_date(hasta)
        if h:
            from datetime import timedelta
            q = q.filter(Order.created_at < (datetime.combine(h, datetime.max.time())))

    q = q.order_by(Order.created_at.desc())
    result = paginate_query(q, page, per_page)
    items_out = []
    for o in result["items"]:
        d = o.to_dict()
        d["parent_name"] = o.parent.full_name if o.parent else ""
        items_out.append(d)
    result["items"] = items_out
    return success_response(result)


# ── GET /pagos/:id ────────────────────────────────────────────────────────────
@bp.route("/<int:order_id>", methods=["GET"])
@any_authenticated
def get_payment(order_id):
    """Detalle de un pago/orden."""
    current = get_current_user()
    role = current.role_name
    order = db.session.get(Order, order_id)
    if not order:
        return error_response("Pago no encontrado.", 404)
    if role == "parent" and order.parent_id != current.id:
        return error_response("No tienes acceso a este pago.", 403)
    if role not in ("parent", "admin", "secretary"):
        return error_response("Sin permisos.", 403)
    data = order.to_dict()
    data["parent_name"] = order.parent.full_name if order.parent else ""
    return success_response(data)


# ── POST /pagos/verificar ─────────────────────────────────────────────────────
@bp.route("/verificar", methods=["POST"])
@any_authenticated
@limiter.limit("20 per minute")
def verify_payment():
    """
    Verifica el pago tras la redirección de MercadoPago.

    Body JSON: {"payment_id": "12345678", "order_id": 1}

    También acepta los params que MercadoPago envía en la URL de retorno:
      ?payment_id=XXX&collection_id=XXX&status=approved&external_reference=ORDER_ID

    Flujo:
      1. El padre completa el pago en MercadoPago.
      2. MP redirige a MP_SUCCESS_URL?payment_id=XXX&...&external_reference=ORDER_ID
      3. El frontend extrae esos params y llama a este endpoint.
      4. Este endpoint consulta la API de MP, valida y aprueba la orden.
    """
    current = get_current_user()
    role = current.role_name

    # Admin también puede verificar (para debugging/soporte)
    if role not in ("parent", "admin"):
        return error_response("Sin permisos para verificar pagos.", 403)

    data = request.get_json(silent=True) or {}

    # Acepta payment_id como string o entero
    payment_id = (
        data.get("payment_id")
        or request.args.get("payment_id")
        or request.args.get("collection_id")
    )
    order_id = (
        data.get("order_id")
        or request.args.get("order_id")
        or request.args.get("external_reference")
    )

    if not payment_id or not order_id:
        return error_response(
            "Se requieren payment_id y order_id. "
            "Envíalos en el body JSON: {\"payment_id\": \"...\", \"order_id\": N}", 400
        )

    order = db.session.get(Order, int(order_id))
    if not order:
        return error_response(f"Orden #{order_id} no encontrada.", 404)
    if role == "parent" and order.parent_id != current.id:
        return error_response("No tienes acceso a esta orden.", 403)

    # Idempotencia
    if order.status == "approved":
        return success_response(
            {"status": "approved", "order_id": order.id, "mp_payment_id": order.mp_payment_id},
            "El pago ya fue confirmado anteriormente.",
        )
    if order.status == "cancelled":
        return error_response("Esta orden fue cancelada y no puede procesarse.", 400)

    # ── Consultar API de MercadoPago ──────────────────────────────────────
    try:
        sdk = _mp_sdk()
        result = sdk.payment().get(str(payment_id))
    except ValueError as e:
        return error_response(str(e), 500)
    except Exception as e:
        logger.error(f"[Pago] Error conectando con MercadoPago: {e}")
        return error_response(f"Error al conectar con MercadoPago: {str(e)}", 502)

    http_status = result.get("status")
    payment = result.get("response", {})

    # Log completo para debugging
    logger.info(
        f"[Pago] MP response para payment_id={payment_id}: "
        f"http_status={http_status}, mp_status={payment.get('status')}, "
        f"amount={payment.get('transaction_amount')}, "
        f"external_ref={payment.get('external_reference')}"
    )

    # SDK v2 puede retornar 200 o 201
    if http_status not in (200, 201):
        logger.error(f"[Pago] MP retornó status HTTP {http_status}. Response: {payment}")
        return error_response(
            f"MercadoPago retornó error HTTP {http_status}. "
            f"Detalle: {payment.get('message', 'Sin mensaje')}. "
            f"Verifica que MP_ACCESS_TOKEN sea correcto en .env.", 502
        )

    mp_status = payment.get("status", "")
    mp_external_ref = str(payment.get("external_reference", ""))
    mp_amount = float(payment.get("transaction_amount", 0) or 0)

    # ── Validaciones de seguridad ─────────────────────────────────────────
    if mp_external_ref and mp_external_ref != str(order.id):
        logger.warning(
            f"[Pago] external_reference mismatch: MP={mp_external_ref}, esperado={order.id}"
        )
        return error_response(
            f"external_reference no coincide. "
            f"MP envió '{mp_external_ref}', esperábamos '{order.id}'.", 400
        )

    if mp_amount > 0 and abs(mp_amount - float(order.total_amount)) > 0.50:
        logger.warning(
            f"[Pago] Monto mismatch: MP={mp_amount}, orden={order.total_amount}"
        )
        return error_response(
            f"El monto del pago (S/ {mp_amount}) no coincide con la orden (S/ {order.total_amount}).", 400
        )

    # ── Procesar según estado de MercadoPago ──────────────────────────────
    if mp_status == "approved":
        enrolled_items = _process_approved_payment(order, payment_id, current)
        return success_response(
            {
                "status": "approved",
                "order_id": order.id,
                "mp_payment_id": str(payment_id),
                "enrolled": enrolled_items,
            },
            "✅ Pago confirmado. Inscripciones activadas exitosamente.",
        )

    elif mp_status == "rejected":
        order.status = "rejected"
        for item in order.items:
            child = db.session.get(Child, item.child_id)
            if child and child.payment_status == "pending":
                child.payment_status = "none"
        db.session.commit()
        motivo = payment.get("status_detail", "Sin detalle")
        return success_response(
            {"status": "rejected", "order_id": order.id, "motivo": motivo},
            f"El pago fue rechazado por MercadoPago. Motivo: {motivo}",
        )

    elif mp_status in ("pending", "in_process", "authorized"):
        return success_response(
            {
                "status": mp_status,
                "order_id": order.id,
                "msg": "El pago aún no fue acreditado. Vuelve a llamar este endpoint en unos minutos.",
            },
            f"Pago en estado '{mp_status}'. Espera la acreditación y vuelve a verificar.",
        )

    else:
        return success_response(
            {"status": mp_status, "order_id": order.id, "raw": payment.get("status_detail")},
            f"Estado del pago: {mp_status}. Contacta soporte si el problema persiste.",
        )


# ── GET /pagos/debug-mp/:payment_id ──────────────────────────────────────────
@bp.route("/debug-mp/<payment_id>", methods=["GET"])
@any_authenticated
def debug_mp_payment(payment_id):
    """
    SOLO ADMIN. Muestra la respuesta RAW de MercadoPago para un payment_id.
    Útil para diagnosticar por qué un pago no se procesa.

    Ejemplo: GET /pagos/debug-mp/12345678
    """
    current = get_current_user()
    if current.role_name != "admin":
        return error_response("Solo el administrador puede usar este endpoint.", 403)

    try:
        sdk = _mp_sdk()
        result = sdk.payment().get(str(payment_id))
        return success_response({
            "http_status": result.get("status"),
            "mp_response": result.get("response", {}),
        }, "Respuesta raw de MercadoPago.")
    except Exception as e:
        return error_response(f"Error: {str(e)}", 502)
