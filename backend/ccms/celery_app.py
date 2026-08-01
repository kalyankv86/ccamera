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
    "check-escalations": {
        "task": "ccms.alerts.escalation.check_escalations",
        "schedule": 60.0,
    },
    "flapping-and-disk-forecast": {
        "task": "ccms.evaluator.flapping.check_flapping_and_disk_forecast",
        "schedule": 300.0,
    },
}

celery_app.conf.task_default_queue = "celery"
celery_app.conf.timezone = "UTC"

# Explicit imports rather than autodiscover_tasks(): autodiscover only finds
# modules literally named "tasks.py" per package, which misses
# scheduler/dispatch.py and watchdog/heartbeat.py. Every task module below uses
# @celery_app.task (not @shared_task) so tasks always bind to this app
# regardless of import order in scripts, tests, or transitive imports.
from ccms.alerts import escalation as _alerts_escalation  # noqa: F401,E402
from ccms.checkers import tasks as _checkers_tasks  # noqa: F401,E402
from ccms.evaluator import flapping as _evaluator_flapping  # noqa: F401,E402
from ccms.notifications import dispatcher as _notifications_dispatcher  # noqa: F401,E402
from ccms.reports import tasks as _reports_tasks  # noqa: F401,E402
from ccms.scheduler import dispatch as _scheduler_dispatch  # noqa: F401,E402
from ccms.watchdog import heartbeat as _watchdog_heartbeat  # noqa: F401,E402
