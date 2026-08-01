"""Simple string templates for alert notifications (FR-07 acceptance criteria:
device name, location, alert type, timestamp, dashboard link)."""

from ccms.models.alert import Alert
from ccms.models.device import Device

DASHBOARD_BASE_URL = "http://localhost:5173"


def render_alert_message(alert: Alert, device: Device, *, recovered: bool = False, downtime_seconds: int | None = None) -> tuple[str, str]:
    location = ", ".join(p for p in [device.building, device.zone] if p)
    link = f"{DASHBOARD_BASE_URL}/devices/{device.id}"

    if recovered:
        subject = f"[CCMS] RECOVERED: {device.name}"
        downtime = f"{downtime_seconds // 60}m {downtime_seconds % 60}s" if downtime_seconds is not None else "unknown"
        body = (
            f"{device.name} ({location or 'unknown location'}) has recovered.\n"
            f"Alert type: {alert.type}\n"
            f"Total downtime: {downtime}\n"
            f"Time: {alert.created_at}\n"
            f"Dashboard: {link}"
        )
        return subject, body

    subject = f"[CCMS] {alert.severity.value.upper()}: {device.name} - {alert.type}"
    body = (
        f"{device.name} ({location or 'unknown location'}) is {alert.type}.\n"
        f"Severity: {alert.severity.value}\n"
        f"Time: {alert.created_at}\n"
        f"Dashboard: {link}"
    )
    return subject, body
