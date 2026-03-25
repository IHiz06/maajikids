"""
MaajiKids — APScheduler Jobs
4 jobs programados que se ejecutan en background.

ORDEN DE ARRANQUE (crítico):
  1. app factory crea la app
  2. db.init_app(app)
  3. scheduler.init_app(app) y scheduler.start()
  4. Los jobs se registran DENTRO del contexto de aplicación

Los jobs NO usan db.session directamente en el scope global;
ejecutan su lógica dentro de un app_context empujado en cada llamada.
"""
from __future__ import annotations
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Instancia global del scheduler (init_scheduler inyecta la app)
_scheduler: BackgroundScheduler | None = None


# ─────────────────────────────────────────────────────────────────────────────
# JOB 1: Limpieza de token_blacklist — cada 60 min
# ─────────────────────────────────────────────────────────────────────────────
def _job_clean_token_blacklist(app):
    with app.app_context():
        try:
            from app.extensions import db
            from app.models.token_blacklist import TokenBlacklist
            from datetime import datetime, timezone, timedelta
            now = datetime.utcnow()
            deleted = db.session.query(TokenBlacklist).filter(
                TokenBlacklist.expires_at < now
            ).delete(synchronize_session=False)
            db.session.commit()
            if deleted:
                logger.info(f"[Scheduler] token_blacklist: {deleted} tokens expirados eliminados.")
        except Exception as e:
            logger.error(f"[Scheduler] Error en job_clean_token_blacklist: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# JOB 2: Auto-delete niños con pago pendiente > 2h — cada 15 min
# ─────────────────────────────────────────────────────────────────────────────
def _job_delete_pending_children(app):
    with app.app_context():
        try:
            from app.extensions import db
            from app.models.child import Child
            from datetime import datetime, timezone, timedelta, timedelta
            cutoff = datetime.utcnow() - timedelta(hours=2)
            to_delete = db.session.query(Child).filter(
                Child.payment_status == "pending",
                Child.created_at < cutoff,
            ).all()
            count = len(to_delete)
            for child in to_delete:
                db.session.delete(child)
            db.session.commit()
            if count:
                logger.info(f"[Scheduler] {count} niños con pago pendiente >2h eliminados.")
        except Exception as e:
            logger.error(f"[Scheduler] Error en job_delete_pending_children: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# JOB 3: Eliminar sesiones de chat IA > 2h — cada 30 min
# ─────────────────────────────────────────────────────────────────────────────
def _job_clean_chat_sessions(app):
    with app.app_context():
        try:
            from app.extensions import db
            from app.models.chat_session import ChatSession
            from datetime import datetime, timezone, timedelta, timedelta
            cutoff = datetime.utcnow() - timedelta(hours=2)
            deleted = db.session.query(ChatSession).filter(
                ChatSession.created_at < cutoff
            ).delete(synchronize_session=False)
            db.session.commit()
            if deleted:
                logger.info(f"[Scheduler] {deleted} sesiones de chat IA eliminadas (cascade mensajes).")
        except Exception as e:
            logger.error(f"[Scheduler] Error en job_clean_chat_sessions: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# JOB 4: Invalidar refresh tokens por inactividad (40 min) — cada 10 min
# ─────────────────────────────────────────────────────────────────────────────
def _job_revoke_inactive_tokens(app):
    with app.app_context():
        try:
            from app.extensions import db
            from app.models.user import User
            from app.models.token_blacklist import TokenBlacklist
            from datetime import datetime, timezone, timedelta, timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=40)
            inactive_users = db.session.query(User).filter(
                User.last_activity < cutoff,
                User.is_active == True,
                User.last_activity.isnot(None),
            ).all()
            # Nota: los refresh tokens no se revocan automáticamente aquí
            # La lógica de inactividad se maneja en el endpoint renovar-token.
            # Este job solo loguea usuarios inactivos para auditoría.
            if inactive_users:
                logger.debug(
                    f"[Scheduler] {len(inactive_users)} usuarios inactivos >40 min detectados."
                )
        except Exception as e:
            logger.error(f"[Scheduler] Error en job_revoke_inactive_tokens: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Inicialización
# ─────────────────────────────────────────────────────────────────────────────
def init_scheduler(app) -> BackgroundScheduler:
    """
    Crea, configura e inicia el scheduler.
    Debe llamarse UNA SOLA VEZ desde el app factory, después de db.init_app().
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("[Scheduler] Ya está corriendo, no se re-inicia.")
        return _scheduler

    _scheduler = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
        timezone="America/Lima",
    )

    # Job 1: cada 60 min
    _scheduler.add_job(
        func=_job_clean_token_blacklist,
        trigger=IntervalTrigger(minutes=60),
        args=[app],
        id="clean_token_blacklist",
        replace_existing=True,
    )

    # Job 2: cada 15 min
    _scheduler.add_job(
        func=_job_delete_pending_children,
        trigger=IntervalTrigger(minutes=15),
        args=[app],
        id="delete_pending_children",
        replace_existing=True,
    )

    # Job 3: cada 30 min
    _scheduler.add_job(
        func=_job_clean_chat_sessions,
        trigger=IntervalTrigger(minutes=30),
        args=[app],
        id="clean_chat_sessions",
        replace_existing=True,
    )

    # Job 4: cada 10 min
    _scheduler.add_job(
        func=_job_revoke_inactive_tokens,
        trigger=IntervalTrigger(minutes=10),
        args=[app],
        id="revoke_inactive_tokens",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("[Scheduler] APScheduler iniciado con 4 jobs activos.")
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] APScheduler detenido.")
