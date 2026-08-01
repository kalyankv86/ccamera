from celery import Celery
from celery.schedules import crontab

from ccms.config import settings

celery_app = Celery("ccms", broker=settings.redis_broker_url, backend=settings.redis_backend_url)

celery_app.conf.task_routes = {
    "ccms.checkers.tasks.run_ping_check": {"queue": "net"},
    "ccms.checkers.tasks.run_snmp_check": {"queue": "net"},
    "ccms.checkers.tasks.run_rtsp_check": {"queue": "stream"},
    "ccms.checkers.tasks.run_image_check": {"queue": "stream"},
    "ccms.checkers.tasks.run_nvr_check": {"queue": "stream"},
    "ccms.notifications.dispatcher.send_notification": {"queue": "notifications"},
    "ccms.reports.tasks.*": {"queue": "reports"},
}

celery_app.conf.beat_schedule = {
    "dispatch-due-checks": {
        "task": "ccms.scheduler.dispatch.enqueue_due_checks",
        "schedule": 15.0,
    },
    "ensure-partitions": {
        "task": "ccms.checkers.tasks.ensure_partitions_task",
        "schedule": crontab(hour=2, minute=0),
    },
    "rollup-retention": {
        "task": "ccms.reports.tasks.rollup_and_retire",
        "schedule": crontab(hour=2, minute=30),
    },
    "monthly-uptime-report": {
        "task": "ccms.reports.tasks.generate_monthly_report",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),
    },
    "heartbeat": {
        "task": "ccms.watchdog.heartbeat.beat",
        "schedule": 60.0,
    },
}

celery_app.conf.task_default_queue = "celery"
celery_app.conf.timezone = "UTC"

# Autodiscover keeps task modules importable without a giant manual include= list.
celery_app.autodiscover_tasks(
    [
        "ccms.checkers",
        "ccms.scheduler",
        "ccms.notifications",
        "ccms.reports",
        "ccms.watchdog",
    ]
)
