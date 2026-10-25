from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "superdato_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes maximum for a single receipt/import task
    worker_prefetch_multiplier=1,
)

# Scheduled periodic tasks via Celery Beat
celery_app.conf.beat_schedule = {
    "sync-gmail-connections-every-30-minutes": {
        "task": "app.domains.integrations.tasks.sync_all_active_google_connections",
        "schedule": crontab(minute="*/30"),
    },
}

# Auto-discover tasks across domain modules
celery_app.autodiscover_tasks([
    "app.domains.integrations",
    "app.domains.receipts",
])


try:
    from celery.signals import worker_process_init

    @worker_process_init.connect
    def on_worker_init(**kwargs):
        """Synchronizes system encryption secrets from database into worker process memory."""
        import asyncio
        from app.core.database import async_session_maker
        from app.core.bootstrap import ensure_system_secrets

        async def _init_secrets():
            async with async_session_maker() as session:
                await ensure_system_secrets(session)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_init_secrets())
        except Exception:
            pass
except Exception:
    pass

