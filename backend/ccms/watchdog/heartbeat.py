"""NFR-07: CCMS monitors itself. A settings row is touched every minute by
Celery beat; external uptime tooling (or a future systemd timer, per SDD 6.3)
can alert if `last_heartbeat_at` goes stale, which means CCMS itself is down."""

from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ccms.db import SessionLocal
from ccms.models.settings import Setting

HEARTBEAT_KEY = "watchdog.last_heartbeat_at"


@shared_task(name="ccms.watchdog.heartbeat.beat")
def beat() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).isoformat()
        stmt = pg_insert(Setting).values(key=HEARTBEAT_KEY, value_jsonb={"at": now})
        stmt = stmt.on_conflict_do_update(index_elements=[Setting.key], set_={"value_jsonb": {"at": now}})
        db.execute(stmt)
        db.commit()
    finally:
        db.close()
