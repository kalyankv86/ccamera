"""NFR-07: CCMS monitors itself. A settings row is touched every minute by
Celery beat; external uptime tooling (or a future systemd timer, per SDD 6.3)
can alert if `last_heartbeat_at` goes stale, which means CCMS itself is down."""

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from ccms.celery_app import celery_app
from ccms.db import SessionLocal
from ccms.models.settings import Setting

HEARTBEAT_KEY = "watchdog.last_heartbeat_at"


@celery_app.task(name="ccms.watchdog.heartbeat.beat")
def beat() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        stmt = pg_insert(Setting).values(key=HEARTBEAT_KEY, value_jsonb={"at": now.isoformat()}, updated_at=now)
        # set_= is an explicit column list for ON CONFLICT DO UPDATE - it does
        # not inherit the column's onupdate=func.now(), which only fires for
        # ORM-level updates, so updated_at must be listed here too.
        stmt = stmt.on_conflict_do_update(
            index_elements=[Setting.key], set_={"value_jsonb": {"at": now.isoformat()}, "updated_at": now}
        )
        db.execute(stmt)
        db.commit()
    finally:
        db.close()
