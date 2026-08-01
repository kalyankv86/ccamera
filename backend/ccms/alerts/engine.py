"""SDD 3.4: consumes status_events. For alert-worthy transitions, creates an
alert row with severity derived from device criticality, applies storm
grouping, and enqueues notification jobs for the criticality's routing table.
Escalation timers are handled separately (alerts/escalation.py, M6)."""

from datetime import datetime, timezone

from ccms.alerts.storm import group_id_for
from ccms.models.alert import Alert
from ccms.models.device import Device
from ccms.models.enums import AlertSeverity, AlertState, Criticality, DeviceState, NotificationChannel, Role
from ccms.models.status_event import StatusEvent
from ccms.models.user import User
from ccms.notifications.dispatcher import send_notification
from ccms.notifications.templates import render_alert_message

_SEVERITY_BY_CRITICALITY = {
    Criticality.CRITICAL: AlertSeverity.CRITICAL,
    Criticality.HIGH: AlertSeverity.WARNING,
    Criticality.NORMAL: AlertSeverity.WARNING,
}


def handle_transition(db, device: Device, event: StatusEvent) -> Alert | None:
    if event.new_state not in (DeviceState.DOWN, DeviceState.UP, DeviceState.DEGRADED):
        return None
    if event.new_state == DeviceState.DEGRADED:
        return None  # quality warnings don't page anyone by default; visible on dashboard only
    if event.suppressed_by_parent:
        return None  # child event recorded but consolidated alert already fired for the parent

    is_recovery = event.new_state == DeviceState.UP and event.old_state == DeviceState.DOWN
    if event.new_state == DeviceState.UP and not is_recovery:
        return None  # UP from DEGRADED/UNKNOWN isn't a recovery worth alerting on

    alert = Alert(
        device_id=device.id,
        group_id=group_id_for(db, device) if event.new_state == DeviceState.DOWN else None,
        type="RECOVERY" if is_recovery else "DOWN",
        severity=_SEVERITY_BY_CRITICALITY[device.criticality],
        state=AlertState.CLOSED if is_recovery else AlertState.OPEN,
        closed_at=datetime.now(timezone.utc) if is_recovery else None,
    )
    db.add(alert)
    db.flush()

    subject, body = render_alert_message(alert, device, recovered=is_recovery, downtime_seconds=event.downtime_seconds)
    for channel, recipient in _recipients_for(db, device):
        send_notification.delay(alert.id, channel.value, recipient, subject, body)

    db.commit()
    return alert


def _recipients_for(db, device: Device) -> list[tuple[NotificationChannel, str]]:
    """FR-07: recipients configurable per device group/criticality. This build's
    default routing (no admin UI for it yet, see M9) is: all active
    Administrators and Security Officers, by email; SMS/WhatsApp use the same
    users' phone numbers when the adapters are configured (they no-op otherwise)."""
    users = (
        db.query(User)
        .filter(User.role.in_([Role.ADMIN, Role.SECURITY_OFFICER]), User.active.is_(True))
        .all()
    )
    recipients: list[tuple[NotificationChannel, str]] = []
    for user in users:
        recipients.append((NotificationChannel.EMAIL, user.email))
        if user.phone:
            recipients.append((NotificationChannel.SMS, user.phone))
            recipients.append((NotificationChannel.WHATSAPP, user.phone))
    return recipients
