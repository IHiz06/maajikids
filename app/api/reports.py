"""
MaajiKids — Blueprint: /reportes
4 endpoints que generan PDFs con logo institucional usando ReportLab.
"""
from flask import Blueprint, request, send_file
import io
from app.extensions import db
from app.models.child import Child
from app.models.workshop import Workshop
from app.models.evaluation import Evaluation
from app.models.ai_recommendation import AIRecommendation
from app.models.order import Order
from app.models.enrollment import Enrollment
from app.services.pdf_service import (
    generate_child_evaluations_pdf,
    generate_child_recommendations_pdf,
    generate_payments_pdf,
    generate_enrollments_pdf,
    generate_workshop_children_pdf,
)
from app.utils.helpers import error_response, parse_date
from app.utils.decorators import any_authenticated, get_current_user

bp = Blueprint("reports", __name__, url_prefix="/reportes")


def _pdf_response(pdf_bytes: bytes, filename: str):
    """Retorna el PDF como respuesta de descarga."""
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


# ── GET /reportes/nino/:id ───────────────────────────────────────────────────
@bp.route("/nino/<int:child_id>", methods=["GET"])
@any_authenticated
def child_report(child_id):
    """
    PDF del niño según ?tipo=evaluaciones o ?tipo=recomendaciones.
    Acceso: admin, teacher (taller asignado), parent (propio hijo).
    """
    current = get_current_user()
    role = current.role_name
    tipo = request.args.get("tipo", "evaluaciones")

    if tipo not in ("evaluaciones", "recomendaciones"):
        return error_response("Parámetro 'tipo' debe ser 'evaluaciones' o 'recomendaciones'.", 400)

    child = db.session.get(Child, child_id)
    if not child or not child.is_active:
        return error_response("Niño no encontrado.", 404)

    # Control de acceso
    if role == "parent" and child.parent_id != current.id:
        return error_response("Sin acceso a este niño.", 403)
    if role == "teacher":
        teacher_ws_ids = {ws.id for ws in Workshop.query.filter_by(teacher_id=current.id).all()}
        child_ws_ids = {e.workshop_id for e in child.enrollments.filter_by(status="active")}
        if not (teacher_ws_ids & child_ws_ids):
            return error_response("Sin acceso a este niño.", 403)
    if role not in ("admin", "teacher", "parent"):
        return error_response("Sin permisos.", 403)

    child_dict = child.to_dict()

    if tipo == "evaluaciones":
        evs = Evaluation.query.filter_by(child_id=child_id).order_by(
            Evaluation.eval_date.desc()
        ).all()
        pdf_bytes = generate_child_evaluations_pdf(child_dict, [e.to_dict() for e in evs])
        filename = f"evaluaciones_{child.full_name.replace(' ', '_')}.pdf"
    else:
        recs_q = AIRecommendation.query.filter_by(child_id=child_id)
        if role == "parent":
            recs_q = recs_q.filter_by(is_visible_to_parent=True)
        recs = recs_q.order_by(AIRecommendation.generated_at.desc()).all()
        pdf_bytes = generate_child_recommendations_pdf(child_dict, [r.to_dict() for r in recs])
        filename = f"recomendaciones_{child.full_name.replace(' ', '_')}.pdf"

    return _pdf_response(pdf_bytes, filename)


# ── GET /reportes/pagos ──────────────────────────────────────────────────────
@bp.route("/pagos", methods=["GET"])
@any_authenticated
def payments_report():
    """
    PDF con reporte de pagos filtrable por período.
    Params: ?desde=YYYY-MM-DD, ?hasta=YYYY-MM-DD
    Solo admin/secretary.
    """
    current = get_current_user()
    if current.role_name not in ("admin", "secretary"):
        return error_response("Sin permisos.", 403)

    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")

    q = Order.query.filter_by(status="approved")
    if desde:
        d = parse_date(desde)
        if d:
            q = q.filter(Order.paid_at >= d)
    if hasta:
        h = parse_date(hasta)
        if h:
            from datetime import timedelta
            q = q.filter(Order.paid_at < (h + timedelta(days=1)))

    orders = q.order_by(Order.paid_at.desc()).all()
    orders_data = []
    for o in orders:
        d = o.to_dict()
        d["parent_name"] = o.parent.full_name if o.parent else ""
        orders_data.append(d)

    pdf_bytes = generate_payments_pdf(orders_data, desde, hasta)
    return _pdf_response(pdf_bytes, "reporte_pagos_maajikids.pdf")


# ── GET /reportes/inscripciones ──────────────────────────────────────────────
@bp.route("/inscripciones", methods=["GET"])
@any_authenticated
def enrollments_report():
    """PDF con reporte de inscripciones activas. Solo admin/secretary."""
    current = get_current_user()
    if current.role_name not in ("admin", "secretary"):
        return error_response("Sin permisos.", 403)

    enrs = Enrollment.query.filter_by(status="active").order_by(
        Enrollment.enrolled_at.desc()
    ).all()

    enrs_data = []
    for e in enrs:
        d = e.to_dict()
        if e.child and e.child.parent:
            d["parent_name"] = e.child.parent.full_name
        else:
            d["parent_name"] = ""
        enrs_data.append(d)

    pdf_bytes = generate_enrollments_pdf(enrs_data)
    return _pdf_response(pdf_bytes, "reporte_inscripciones_maajikids.pdf")


# ── GET /reportes/taller/:id/ninos ───────────────────────────────────────────
@bp.route("/taller/<int:workshop_id>/ninos", methods=["GET"])
@any_authenticated
def workshop_children_report(workshop_id):
    """
    PDF con lista de niños inscritos en un taller.
    Acceso: admin o teacher del taller.
    """
    current = get_current_user()
    role = current.role_name

    workshop = db.session.get(Workshop, workshop_id)
    if not workshop:
        return error_response("Taller no encontrado.", 404)

    if role == "teacher" and workshop.teacher_id != current.id:
        return error_response("Sin acceso a este taller.", 403)
    if role not in ("admin", "teacher"):
        return error_response("Sin permisos.", 403)

    enrs = Enrollment.query.filter_by(workshop_id=workshop_id, status="active").all()
    children_data = []
    for e in enrs:
        child = db.session.get(Child, e.child_id)
        if child and child.is_active:
            cd = child.to_dict()
            cd["parent_name"] = child.parent.full_name if child.parent else ""
            children_data.append(cd)

    ws_dict = workshop.to_dict()
    ws_dict["teacher_name"] = workshop.teacher.full_name if workshop.teacher else "Sin asignar"

    pdf_bytes = generate_workshop_children_pdf(ws_dict, children_data)
    filename = f"ninos_{workshop.title.replace(' ', '_')[:30]}.pdf"
    return _pdf_response(pdf_bytes, filename)
