"""
MaajiKids — Blueprint: /evaluaciones
5 endpoints. Solo niños con payment_status='verified' y dni_verified=True.
"""
from datetime import date
from flask import Blueprint, request
from app.extensions import db
from app.models.evaluation import Evaluation
from app.models.child import Child
from app.models.workshop import Workshop
from app.models.enrollment import Enrollment
from app.utils.helpers import success_response, error_response, paginate_query, parse_date
from app.utils.decorators import any_authenticated, get_current_user

bp = Blueprint("evaluations", __name__, url_prefix="/evaluaciones")


def _validate_score(value, field_name: str):
    """Valida que el puntaje esté entre 0.0 y 10.0."""
    try:
        v = float(value)
        if not (0.0 <= v <= 10.0):
            raise ValueError
        return v, None
    except (TypeError, ValueError):
        return None, f"{field_name} debe ser un número entre 0.0 y 10.0."


# ── GET /evaluaciones/ ───────────────────────────────────────────────────────
@bp.route("/", methods=["GET"])
@any_authenticated
def list_evaluations():
    """
    Lista evaluaciones.
    Params: ?nino_id=X, ?taller_id=X, ?teacher_id=X, ?page=, ?per_page=
    - Teacher: solo evaluaciones de sus talleres asignados.
    - Parent: solo evaluaciones de sus hijos.
    - Admin: todas.
    """
    current = get_current_user()
    role = current.role_name

    nino_id = request.args.get("nino_id", type=int)
    taller_id = request.args.get("taller_id", type=int)
    teacher_id = request.args.get("teacher_id", type=int)
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    if role not in ("admin", "teacher", "parent"):
        return error_response("Sin permisos.", 403)

    q = Evaluation.query

    if role == "teacher":
        # Solo evaluaciones de talleres asignados a este teacher
        teacher_ws_ids = [
            ws.id for ws in Workshop.query.filter_by(teacher_id=current.id).all()
        ]
        q = q.filter(Evaluation.workshop_id.in_(teacher_ws_ids))
        if taller_id:
            if taller_id not in teacher_ws_ids:
                return error_response("No tienes acceso a ese taller.", 403)
            q = q.filter_by(workshop_id=taller_id)

    elif role == "parent":
        # Solo evaluaciones de sus hijos
        child_ids = [c.id for c in Child.query.filter_by(parent_id=current.id, is_active=True).all()]
        q = q.filter(Evaluation.child_id.in_(child_ids))

    elif role == "admin":
        if taller_id:
            q = q.filter_by(workshop_id=taller_id)
        if teacher_id:
            q = q.filter_by(teacher_id=teacher_id)

    if nino_id:
        q = q.filter_by(child_id=nino_id)

    q = q.order_by(Evaluation.eval_date.desc())
    result = paginate_query(q, page, per_page)
    result["items"] = [e.to_dict() for e in result["items"]]
    return success_response(result)


# ── POST /evaluaciones/ ──────────────────────────────────────────────────────
@bp.route("/", methods=["POST"])
@any_authenticated
def create_evaluation():
    """
    Crea evaluación. Teacher evalúa solo niños de sus talleres
    con payment_status='verified' y dni_verified=True.
    """
    current = get_current_user()
    role = current.role_name

    if role not in ("teacher", "admin"):
        return error_response("Solo profesores o administradores pueden crear evaluaciones.", 403)

    data = request.get_json(silent=True) or {}
    child_id = data.get("child_id")
    workshop_id = data.get("workshop_id")
    eval_date_str = data.get("eval_date")

    if not all([child_id, workshop_id, eval_date_str]):
        return error_response("Campos requeridos: child_id, workshop_id, eval_date.", 400)

    child = db.session.get(Child, int(child_id))
    if not child or not child.is_active:
        return error_response("Niño no encontrado.", 404)

    workshop = db.session.get(Workshop, int(workshop_id))
    if not workshop:
        return error_response("Taller no encontrado.", 404)

    # Validaciones de acceso (teacher)
    if role == "teacher":
        if workshop.teacher_id != current.id:
            return error_response("No tienes acceso a ese taller.", 403)

    # Validaciones requeridas del niño
    if child.payment_status != "verified":
        return error_response(
            f"'{child.full_name}' no tiene pago verificado. No puede ser evaluado.", 400
        )
    if not child.dni_verified:
        return error_response(
            f"'{child.full_name}' no tiene DNI verificado. No puede ser evaluado.", 400
        )

    # Verificar que el niño esté inscrito en el taller
    enrollment = Enrollment.query.filter_by(
        child_id=child.id, workshop_id=workshop.id, status="active"
    ).first()
    if not enrollment:
        return error_response(
            f"'{child.full_name}' no está inscrito en '{workshop.title}'.", 400
        )

    eval_date = parse_date(eval_date_str)
    if not eval_date:
        return error_response("eval_date debe tener formato YYYY-MM-DD.", 400)
    if eval_date > date.today():
        return error_response("La fecha de evaluación no puede ser futura.", 400)

    # Puntajes
    sc, err = _validate_score(data.get("score_cognitive"), "score_cognitive")
    if err:
        return error_response(err, 400)
    sm, err = _validate_score(data.get("score_motor"), "score_motor")
    if err:
        return error_response(err, 400)
    sl, err = _validate_score(data.get("score_language"), "score_language")
    if err:
        return error_response(err, 400)
    ss, err = _validate_score(data.get("score_social"), "score_social")
    if err:
        return error_response(err, 400)

    evaluation = Evaluation(
        child_id=child.id,
        workshop_id=workshop.id,
        teacher_id=current.id,
        eval_date=eval_date,
        score_cognitive=sc,
        score_motor=sm,
        score_language=sl,
        score_social=ss,
        observations=data.get("observations"),
    )
    db.session.add(evaluation)
    db.session.commit()

    return success_response(evaluation.to_dict(), "Evaluación registrada exitosamente.", 201)


# ── GET /evaluaciones/:id ────────────────────────────────────────────────────
@bp.route("/<int:eval_id>", methods=["GET"])
@any_authenticated
def get_evaluation(eval_id):
    """Detalle de una evaluación."""
    current = get_current_user()
    role = current.role_name

    ev = db.session.get(Evaluation, eval_id)
    if not ev:
        return error_response("Evaluación no encontrada.", 404)

    if role == "teacher" and ev.teacher_id != current.id:
        return error_response("No tienes acceso a esta evaluación.", 403)
    if role == "parent":
        child = db.session.get(Child, ev.child_id)
        if not child or child.parent_id != current.id:
            return error_response("No tienes acceso a esta evaluación.", 403)

    return success_response(ev.to_dict())


# ── PATCH /evaluaciones/:id ──────────────────────────────────────────────────
@bp.route("/<int:eval_id>", methods=["PATCH"])
@any_authenticated
def update_evaluation(eval_id):
    """Actualiza puntajes u observaciones. Teacher solo su propia evaluación."""
    current = get_current_user()
    role = current.role_name

    if role not in ("teacher", "admin"):
        return error_response("Sin permisos para editar evaluaciones.", 403)

    ev = db.session.get(Evaluation, eval_id)
    if not ev:
        return error_response("Evaluación no encontrada.", 404)

    if role == "teacher" and ev.teacher_id != current.id:
        return error_response("Solo puedes editar tus propias evaluaciones.", 403)

    data = request.get_json(silent=True) or {}

    if "score_cognitive" in data:
        v, err = _validate_score(data["score_cognitive"], "score_cognitive")
        if err:
            return error_response(err, 400)
        ev.score_cognitive = v
    if "score_motor" in data:
        v, err = _validate_score(data["score_motor"], "score_motor")
        if err:
            return error_response(err, 400)
        ev.score_motor = v
    if "score_language" in data:
        v, err = _validate_score(data["score_language"], "score_language")
        if err:
            return error_response(err, 400)
        ev.score_language = v
    if "score_social" in data:
        v, err = _validate_score(data["score_social"], "score_social")
        if err:
            return error_response(err, 400)
        ev.score_social = v
    if "observations" in data:
        ev.observations = data["observations"]
    if "eval_date" in data:
        d = parse_date(data["eval_date"])
        if not d:
            return error_response("eval_date inválido.", 400)
        ev.eval_date = d

    db.session.commit()
    return success_response(ev.to_dict(), "Evaluación actualizada exitosamente.")


# ── DELETE /evaluaciones/:id ─────────────────────────────────────────────────
@bp.route("/<int:eval_id>", methods=["DELETE"])
@any_authenticated
def delete_evaluation(eval_id):
    """Elimina físicamente una evaluación. Solo admin."""
    current = get_current_user()
    if current.role_name != "admin":
        return error_response("Solo el administrador puede eliminar evaluaciones.", 403)

    ev = db.session.get(Evaluation, eval_id)
    if not ev:
        return error_response("Evaluación no encontrada.", 404)

    db.session.delete(ev)
    db.session.commit()
    return success_response(message="Evaluación eliminada exitosamente.")
