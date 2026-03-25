"""
MaajiKids — Blueprint: /ordenes
5 endpoints. Carrito multi-ítem con lógica de reutilización de órdenes pending.
"""
from flask import Blueprint, request
from app.extensions import db
from app.models.order import Order, OrderItem
from app.models.child import Child
from app.models.workshop import Workshop
from app.models.enrollment import Enrollment
from app.utils.helpers import (
    success_response, error_response, paginate_query, now_utc,
)
from app.utils.decorators import any_authenticated, get_current_user
import mercadopago
from flask import current_app

bp = Blueprint("orders", __name__, url_prefix="/ordenes")


def _mp_sdk():
    return mercadopago.SDK(current_app.config.get("MP_ACCESS_TOKEN", ""))


# ── GET /ordenes/ ─────────────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
@any_authenticated
def list_orders():
    """
    Lista órdenes.
    Parent auto-filtra las suyas.
    Admin/secretary ven todas.
    Params: ?nino_id=X, ?estado=pending|approved|rejected|cancelled, ?page=, ?per_page=
    """
    current = get_current_user()
    role = current.role_name
    nino_id = request.args.get("nino_id", type=int)
    estado = request.args.get("estado")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    q = Order.query

    if role == "parent":
        q = q.filter_by(parent_id=current.id)
    elif role not in ("admin", "secretary"):
        return error_response("Sin permisos.", 403)

    if estado:
        q = q.filter_by(status=estado)

    if nino_id:
        # Filtra órdenes que contengan un OrderItem del niño especificado
        q = q.join(OrderItem).filter(OrderItem.child_id == nino_id)

    q = q.order_by(Order.created_at.desc())
    result = paginate_query(q, page, per_page)
    result["items"] = [o.to_dict() for o in result["items"]]
    return success_response(result)


# ── POST /ordenes/ ────────────────────────────────────────────────────────────
@bp.route("/", methods=["POST"])
@any_authenticated
def create_order():
    """
    Crea una orden con uno o más ítems {child_id, workshop_id}.

    Lógica de reutilización (v5.0):
      - Si hay enrollment activo para child+workshop → 409
      - Si hay orden 'approved' para child+workshop → 409
      - Si hay orden 'pending' para el MISMO child+workshop → REUTILIZA (200)
      - Si child.payment_status='pending' por OTRO taller → 400
      - Si rejected/cancelled → crea nueva
    """
    current = get_current_user()
    if current.role_name != "parent":
        return error_response("Solo los padres pueden crear órdenes.", 403)

    data = request.get_json(silent=True) or {}
    items_input = data.get("items", [])

    if not items_input or not isinstance(items_input, list):
        return error_response("Se requiere una lista de 'items' con {child_id, workshop_id}.", 400)

    # ── Paso 1: Validaciones básicas de cada ítem ──────────────────────────
    validated_items = []
    for item in items_input:
        child_id = item.get("child_id")
        workshop_id = item.get("workshop_id")

        if not child_id or not workshop_id:
            return error_response("Cada ítem debe tener child_id y workshop_id.", 400)

        child = db.session.get(Child, int(child_id))
        if not child or not child.is_active:
            return error_response(f"Niño {child_id} no encontrado.", 404)
        if child.parent_id != current.id:
            return error_response(f"El niño {child_id} no te pertenece.", 403)

        workshop = db.session.get(Workshop, int(workshop_id))
        if not workshop or not workshop.is_active:
            return error_response(f"Taller {workshop_id} no encontrado o no activo.", 404)
        if workshop.is_full:
            return error_response(f"El taller '{workshop.title}' no tiene cupos disponibles.", 400)

        # Validar rango de edad
        age = child.age_in_months
        if not (workshop.age_min <= age <= workshop.age_max):
            return error_response(
                f"'{child.full_name}' ({age} meses) no cumple el rango de edad del taller "
                f"'{workshop.title}' ({workshop.age_min}-{workshop.age_max} meses).", 400
            )

        validated_items.append({"child": child, "workshop": workshop})

    # ── Paso 2: Por cada ítem verificar estado e intentar reutilizar ───────
    for vi in validated_items:
        child = vi["child"]
        workshop = vi["workshop"]

        # 2a. Inscripción activa ya existe → no puede comprar de nuevo
        active_enroll = Enrollment.query.filter_by(
            child_id=child.id, workshop_id=workshop.id, status="active"
        ).first()
        if active_enroll:
            return error_response(f"'{child.full_name}' ya está inscrito en '{workshop.title}'.", 409)

        # 2b. Orden approved para este child+workshop → no puede volver a comprar
        approved_item = (
            db.session.query(OrderItem)
            .join(Order)
            .filter(
                OrderItem.child_id == child.id,
                OrderItem.workshop_id == workshop.id,
                Order.status == "approved",
            )
            .first()
        )
        if approved_item:
            return error_response(f"'{child.full_name}' ya pagó el taller '{workshop.title}'.", 409)

        # 2c. Orden pending para el MISMO child+workshop → REUTILIZAR (solo un ítem)
        pending_item = (
            db.session.query(OrderItem)
            .join(Order)
            .filter(
                OrderItem.child_id == child.id,
                OrderItem.workshop_id == workshop.id,
                Order.status == "pending",
                Order.parent_id == current.id,
            )
            .first()
        )
        if pending_item:
            # Solo reutilizar si la petición es de un solo ítem
            if len(validated_items) == 1:
                existing_order = db.session.get(Order, pending_item.order_id)
                return success_response(
                    {**existing_order.to_dict(), "orden_existente": True},
                    "Se reutilizó una orden pendiente existente. Procede al pago.",
                    200,
                )
            # Multi-ítem con uno ya pendiente: continuar (se usará la misma orden si existe)
            vi["pending_order_id"] = pending_item.order_id
            continue

        # 2d. Niño con payment_status='pending' pero NO es el mismo taller → bloquear
        # (significa que hay otra orden pending de un taller diferente)
        if child.payment_status == "pending":
            return error_response(
                f"El niño '{child.full_name}' tiene un pago pendiente de otro taller. "
                f"Completa o cancela ese pago primero.", 400
            )

    # ── Paso 3: Crear nueva orden ──────────────────────────────────────────
    total = sum(float(vi["workshop"].price) for vi in validated_items)

    new_order = Order(
        parent_id=current.id,
        status="pending",
        total_amount=total,
    )
    db.session.add(new_order)
    db.session.flush()

    for vi in validated_items:
        child = vi["child"]
        workshop = vi["workshop"]
        order_item = OrderItem(
            order_id=new_order.id,
            child_id=child.id,
            workshop_id=workshop.id,
            unit_price=workshop.price,
        )
        db.session.add(order_item)
        # Marcar niño como pago pending
        child.payment_status = "pending"

    db.session.commit()

    return success_response(
        {**new_order.to_dict(), "orden_existente": False},
        "Orden creada exitosamente. Procede al pago.",
        201,
    )

# ── GET /ordenes/:id ─────────────────────────────────────────────────────────
@bp.route("/<int:order_id>", methods=["GET"])
@any_authenticated
def get_order(order_id):
    """Detalle de una orden con sus ítems."""
    current = get_current_user()
    order = db.session.get(Order, order_id)
    if not order:
        return error_response("Orden no encontrada.", 404)

    role = current.role_name
    if role == "parent" and order.parent_id != current.id:
        return error_response("No tienes acceso a esta orden.", 403)
    if role not in ("parent", "admin", "secretary"):
        return error_response("Sin permisos.", 403)

    return success_response(order.to_dict())


# ── POST /ordenes/:id/pago ────────────────────────────────────────────────────
@bp.route("/<int:order_id>/pago", methods=["POST"])
@any_authenticated
def create_payment_preference(order_id):
    """
    Genera preferencia de pago en MercadoPago.
    Siempre genera una nueva preferencia (por si la anterior expiró).
    Retorna {preference_id, checkout_url}.
    """
    current = get_current_user()
    if current.role_name != "parent":
        return error_response("Solo los padres pueden iniciar pagos.", 403)

    order = db.session.get(Order, order_id)
    if not order:
        return error_response("Orden no encontrada.", 404)
    if order.parent_id != current.id:
        return error_response("No tienes acceso a esta orden.", 403)
    if order.status == "approved":
        return error_response("Esta orden ya fue pagada.", 400)
    if order.status == "cancelled":
        return error_response("Esta orden fue cancelada.", 400)

    # Construir preferencia de MercadoPago
    mp_items = []
    for item in order.items:
        mp_items.append({
            "id": str(item.workshop_id),
            "title": item.workshop.title if item.workshop else f"Taller #{item.workshop_id}",
            "description": f"Inscripción de {item.child.full_name if item.child else ''} - {item.workshop.title if item.workshop else ''}",
            "quantity": 1,
            "unit_price": float(item.unit_price),
            "currency_id": "PEN",
        })

    preference_data = {
        "items": mp_items,
        "payer": {
            "name": current.first_name,
            "surname": current.last_name,
            "email": current.email,
        },
        "external_reference": str(order.id),
        "back_urls": {
            "success": current_app.config.get("MP_SUCCESS_URL"),
            "failure": current_app.config.get("MP_FAILURE_URL"),
            "pending": current_app.config.get("MP_PENDING_URL"),
        },
        "auto_return": "approved",
        "statement_descriptor": "MAAJIKIDS",
    }

    try:
        sdk = _mp_sdk()
        result = sdk.preference().create(preference_data)
        response_data = result.get("response", {})

        if result.get("status") not in (200, 201):
            return error_response("Error al crear la preferencia de pago en MercadoPago.", 502)

        preference_id = response_data.get("id")
        # sandbox: init_point, producción: también init_point
        checkout_url = response_data.get("init_point") or response_data.get("sandbox_init_point")

        # Guardar preference_id en la orden
        order.mp_preference_id = preference_id
        db.session.commit()

        return success_response({
            "preference_id": preference_id,
            "checkout_url": checkout_url,
            "order_id": order.id,
        }, "Preferencia de pago creada.")

    except Exception as e:
        return error_response(f"Error conectando con MercadoPago: {str(e)}", 502)


# ── DELETE /ordenes/:id ───────────────────────────────────────────────────────
@bp.route("/<int:order_id>", methods=["DELETE"])
@any_authenticated
def cancel_order(order_id):
    """
    Cancela una orden pendiente (status='cancelled').
    Revierte payment_status de niños a 'none'.
    """
    current = get_current_user()
    order = db.session.get(Order, order_id)
    if not order:
        return error_response("Orden no encontrada.", 404)

    role = current.role_name
    if role == "parent" and order.parent_id != current.id:
        return error_response("No tienes acceso a esta orden.", 403)
    if role not in ("parent", "admin"):
        return error_response("Sin permisos para cancelar órdenes.", 403)
    if order.status != "pending":
        return error_response(f"Solo se pueden cancelar órdenes en estado 'pending'. Estado actual: {order.status}.", 400)

    order.status = "cancelled"

    # Revertir payment_status de los niños a 'none'
    for item in order.items:
        child = db.session.get(Child, item.child_id)
        if child and child.payment_status == "pending":
            child.payment_status = "none"

    db.session.commit()
    return success_response(message="Orden cancelada exitosamente.")
