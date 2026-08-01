"""SDD 3.1: dispatch is a single static Celery-beat entry (every 15s) that reads
per-device due-times from the database, rather than a custom dynamic beat
scheduler. This is the concrete resolution of "beat reads DB every minute" for a
no-Docker, plain-Celery deployment.
"""

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ccms.celery_app import celery_app
from ccms.db import SessionLocal
from ccms.evaluator.maintenance import is_device_in_maintenance
from ccms.models.device import Device

# (db column, interval column, task name, max jitter seconds)
_CHECK_SPECS = [
    ("next_ping_check_at", "ping_interval_s", "ccms.checkers.tasks.run_ping_check", 15),
    ("next_rtsp_check_at", "rtsp_interval_s", "ccms.checkers.tasks.run_rtsp_check", 15),
    ("next_nvr_check_at", "nvr_interval_s", "ccms.checkers.tasks.run_nvr_check", 15),
    ("next_image_check_at", "image_interval_s", "ccms.checkers.tasks.run_image_check", 15),
]


@celery_app.task(name="ccms.scheduler.dispatch.enqueue_due_checks")
def enqueue_due_checks() -> int:
    now = datetime.now(timezone.utc)
    enqueued = 0
    db = SessionLocal()
    try:
        devices = db.execute(select(Device).where(Device.active.is_(True))).scalars().all()
        for device in devices:
            maintenance = is_device_in_maintenance(db, device)
            for due_col, interval_col, task_name, max_jitter in _CHECK_SPECS:
                due_at = getattr(device, due_col)
                if due_at is not None and due_at.tzinfo is None:
                    due_at = due_at.replace(tzinfo=timezone.utc)
                if due_at is not None and due_at > now:
                    continue
                celery_app.send_task(task_name, args=[device.id], kwargs={"maintenance_flag": maintenance})
                enqueued += 1
                interval = getattr(device, interval_col)
                jitter = random.uniform(0, max_jitter)
                setattr(device, due_col, now + timedelta(seconds=interval + jitter))
        db.commit()
    finally:
        db.close()
    return enqueued
