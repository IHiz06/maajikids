"""
MaajiKids Backend — App Factory
Crea y configura la aplicación Flask con todos sus componentes.

ORDEN DE INICIALIZACIÓN (crítico para evitar import circulares):
  1. Crear app Flask
  2. Cargar configuración
  3. Inicializar extensiones (db, jwt, mail, cors, limiter, talisman)
  4. Registrar blueprints
  5. Configurar JWT callbacks (blacklist check)
  6. Crear tablas y datos iniciales (solo en dev)
  7. Iniciar APScheduler (al final, con app ya configurada)
"""
import logging
import os
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager

from app.config import config_by_name
from app.extensions import db, jwt, mail, migrate, cors, limiter, talisman

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    """
    App Factory. Llama a esta función desde run.py o desde los tests.
    config_name: 'development' | 'production' | 'testing' | None (auto desde FLASK_ENV)
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, static_folder="../static")
    cfg = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg)

    # ── Extensiones ────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # CORS: acepta cualquier origen (según requerimiento del documento)
    cors.init_app(
        app,
        resources={r"/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        supports_credentials=False,
    )

    # Rate limiter
    limiter.init_app(app)

    # Talisman (seguridad HTTP headers) — desactivado en dev para evitar problemas con Swagger
    if config_name == "production":
        talisman.init_app(
            app,
            force_https=True,
            strict_transport_security=True,
            content_security_policy=False,  # El frontend maneja su propio CSP
        )

    # ── JWT ────────────────────────────────────────────────────────────────
    jwt.init_app(app)
    _configure_jwt(app)

    # ── Blueprints ─────────────────────────────────────────────────────────
    _register_blueprints(app)

    # ── Handlers de error globales ─────────────────────────────────────────
    _register_error_handlers(app)

    # ── Inicializar BD + datos seed en dev/testing ─────────────────────────
    with app.app_context():
        _init_database(app)

    # ── APScheduler (al final, fuera del app_context del with) ────────────
    if config_name != "testing":
        from app.services.scheduler_service import init_scheduler
        init_scheduler(app)
        logger.info("[App] APScheduler iniciado.")

    logger.info(f"[App] MaajiKids Backend iniciado en modo '{config_name}'.")
    logger.info(f"[App] Documentación API: /api/docs")
    return app


# ── JWT Callbacks ─────────────────────────────────────────────────────────────
def _configure_jwt(app: Flask):
    """Configura callbacks del JWT (blacklist, errores)."""

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Verifica si el JTI está en token_blacklist de PostgreSQL."""
        from app.models.token_blacklist import TokenBlacklist
        jti = jwt_payload.get("jti")
        return db.session.query(TokenBlacklist).filter_by(jti=jti).first() is not None

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "message": "Token revocado. Inicia sesión nuevamente.",
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "message": "Token expirado. Renueva tu sesión.",
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "success": False,
            "message": "Token inválido.",
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "success": False,
            "message": "Se requiere autenticación. Incluye el header Authorization: Bearer <token>.",
        }), 401


# ── Registro de Blueprints ────────────────────────────────────────────────────
def _register_blueprints(app: Flask):
    from app.api.auth import bp as auth_bp
    from app.api.users import bp as users_bp
    from app.api.roles import bp as roles_bp
    from app.api.workshops import bp as workshops_bp
    from app.api.children import bp as children_bp
    from app.api.emergency_contacts import bp as ec_bp
    from app.api.orders import bp as orders_bp
    from app.api.payments import bp as payments_bp
    from app.api.evaluations import bp as evals_bp
    from app.api.ai import bp as ai_bp
    from app.api.contact import bp as contact_bp
    from app.api.reports import bp as reports_bp
    from app.api.swagger import bp as swagger_bp

    blueprints = [
        auth_bp, users_bp, roles_bp, workshops_bp, children_bp,
        ec_bp, orders_bp, payments_bp, evals_bp, ai_bp,
        contact_bp, reports_bp, swagger_bp,
    ]
    for bp in blueprints:
        app.register_blueprint(bp)

    # Health check
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "MaajiKids Backend v5.0"})

    @app.route("/")
    def root():
        return jsonify({
            "service": "MaajiKids Backend API v5.0",
            "docs": "/api/docs",
            "health": "/health",
        })

    logger.info(f"[App] {len(blueprints)} blueprints registrados.")


# ── Error Handlers ────────────────────────────────────────────────────────────
def _register_error_handlers(app: Flask):

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success": False, "message": "Solicitud inválida.", "error": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Recurso no encontrado."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "message": "Método HTTP no permitido."}), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"success": False, "message": "Conflicto con el estado actual del recurso."}), 409

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"success": False, "message": "Datos de entrada inválidos.", "error": str(e)}), 422

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"success": False, "message": "Demasiadas solicitudes. Intenta más tarde."}), 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        logger.error(f"[500] Error interno: {e}")
        return jsonify({"success": False, "message": "Error interno del servidor."}), 500


# ── Inicialización de BD y datos semilla ──────────────────────────────────────
def _init_database(app: Flask):
    """Crea todas las tablas y los 4 roles del sistema si no existen."""
    db.create_all()
    _seed_roles()
    logger.info("[DB] Tablas verificadas/creadas.")


def _seed_roles():
    """Crea los 4 roles del sistema si no existen. Idempotente."""
    from app.models.role import Role

    system_roles = [
        {
            "name": "admin",
            "description": "Administrador del sistema. Control total.",
            "is_system": True,
            "permissions": Role.SYSTEM_ROLES["admin"],
        },
        {
            "name": "teacher",
            "description": "Especialista / Educadora del centro.",
            "is_system": True,
            "permissions": Role.SYSTEM_ROLES["teacher"],
        },
        {
            "name": "secretary",
            "description": "Secretaría / Recepción.",
            "is_system": True,
            "permissions": Role.SYSTEM_ROLES["secretary"],
        },
        {
            "name": "parent",
            "description": "Padre, madre o tutor.",
            "is_system": True,
            "permissions": Role.SYSTEM_ROLES["parent"],
        },
    ]

    created = 0
    for role_data in system_roles:
        existing = Role.query.filter_by(name=role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.session.add(role)
            created += 1

    if created:
        db.session.commit()
        logger.info(f"[Seed] {created} roles del sistema creados.")

    # Crear admin por defecto si no existe ningún usuario admin
    _seed_default_admin()


def _seed_default_admin():
    """Crea el usuario admin por defecto si no existe ninguno. Solo en dev."""
    import os
    if os.environ.get("FLASK_ENV") == "production":
        return  # No crear admin por defecto en producción

    from app.models.user import User
    from app.models.role import Role

    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        return

    existing_admin = User.query.filter(
        User.role_id == admin_role.id
    ).first()

    if not existing_admin:
        admin = User(
            email="admin@maajikids.com",
            role_id=admin_role.id,
            first_name="ADMINISTRADOR",
            last_name="MAAJIKIDS",
            is_active=True,
            email_verified=True,
        )
        admin.set_password("Admin123!")
        db.session.add(admin)
        db.session.commit()
        logger.info(
            "[Seed] ⚠️  Admin por defecto creado: admin@maajikids.com / Admin123! "
            "— CAMBIA ESTA CONTRASEÑA EN PRODUCCIÓN."
        )
