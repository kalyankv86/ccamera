"""FR-08: unacknowledged critical alerts escalate along a configurable chain
(e.g. Technician at 0 min, Security Officer at 30 min, Admin/IT Head at
60 min). Escalation stops on acknowledgement or recovery - both close the
alert (state != OPEN), and check_escalations() only ever looks at OPEN alerts,
so that's automatic rather than needing an explicit "cancel timer" step.

Implemented as a periodic sweep (Celery beat, every 60s) rather than
per-alert scheduled countdown tasks: a sweep survives worker/Redis restarts
naturally (it just re-evaluates elapsed time against escalations already
fired), matching the same "scheduler reads DB state" pattern used by
ccms.scheduler.dispatch for checks.
"""

from datetime import datetime, timezone

from ccms.celery_app import celery_app
from ccms.db import SessionLocal
from ccms.models.alert import Alert, Escalation
from ccms.models.enums import AlertSeverity, AlertState, Role
from ccms.models.settings import Setting
from ccms.models.user import User
from ccms.notifications.dispatcher import send_notification
from ccms.notifications.templates import render_alert_message
from ccms.models.device import Device

SETTINGS_KEY = "escalation_policy"

# tier -> (delay_minutes, role). Per-severity, ordered by tier.
DEFAULT_POLICY: dict[str, list[dict]] = {
    AlertSeverity.CRITICAL.value: [
        {"tier": 1, "delay_min": 0, "role": Role.TECHNICIAN.value},
        {"tier": 2, "delay_min": 30, "role": Role.SECURITY_OFFICER.value},
        {"tier": 3, "delay_min": 60, "role": Role.ADMIN.value},
    ],
    AlertSeverity.WARNING.value: [
        {"tier": 1, "delay_min": 0, "role": Role.SECURITY_OFFICER.value},
    ],
    AlertSeverity.INFO.value: [],
}


def _policy_for(db, severity: AlertSeverity) -> list[dict]:
    row = db.get(Setting, SETTINGS_KEY)
    policy = row.value_jsonb if row else DEFAULT_POLICY
    return policy.get(severity.value, [])


@celery_app.task(name="ccms.alerts.escalation.check_escalations")
def check_escalations() -> int:
    fired = 0
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        open_alerts = db.query(Alert).filter(Alert.state == AlertState.OPEN).all()

        for alert in open_alerts:
            tiers = _policy_for(db, alert.severity)
            if not tiers:
                continue

            already_fired = {
                e.tier for e in db.query(Escalation).filter(Escalation.alert_id == alert.id).all()
            }
            created_at = alert.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            elapsed_min = (now - created_at).total_seconds() / 60

            device = db.get(Device, alert.device_id)

            for tier_spec in tiers:
                tier = tier_spec["tier"]
                if tier in already_fired or elapsed_min < tier_spec["delay_min"]:
                    continue

                role = Role(tier_spec["role"])
                users = db.query(User).filter(User.role == role, User.active.is_(True)).all()
                notified_ids = [u.id for u in users]

                db.add(Escalation(alert_id=alert.id, tier=tier, notified_user_ids=notified_ids))
                db.commit()
                fired += 1

                subject, body = render_alert_message(alert, device)
                subject = f"[ESCALATION tier {tier}] {subject}"
                for user in users:
                    send_notification.delay(alert.id, "email", user.email, subject, body)
    finally:
        db.close()
    return fired
