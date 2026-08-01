"""FR-11: flapping detection (>X down/up cycles in Y hours) and a simple
predictive indicator - NVR disk-full forecast, warning at a projected 14 days
before capacity is reached. Runs as a Celery beat sweep every 5 minutes."""

from datetime import datetime, timedelta, timezone

from ccms.celery_app import celery_app
from ccms.db import SessionLocal
from ccms.models.alert import Alert
from ccms.models.check_result import CheckResult
from ccms.models.device import Device
from ccms.models.enums import AlertSeverity, AlertState, CheckType, DeviceState, DeviceType
from ccms.models.status_event import StatusEvent

FLAP_CYCLES = 3
FLAP_WINDOW_HOURS = 1
FLAP_ALERT_COOLDOWN_HOURS = 1

DISK_FORECAST_LOOKBACK_DAYS = 7
DISK_FORECAST_WARNING_DAYS = 14


@celery_app.task(name="ccms.evaluator.flapping.check_flapping_and_disk_forecast")
def check_flapping_and_disk_forecast() -> dict:
    db = SessionLocal()
    result = {"flapping": 0, "disk_forecast": 0}
    try:
        now = datetime.now(timezone.utc)

        # --- Flapping: >= FLAP_CYCLES DOWN transitions within the window ---
        window_start = now - timedelta(hours=FLAP_WINDOW_HOURS)
        devices = db.query(Device).filter(Device.active.is_(True)).all()
        for device in devices:
            down_count = (
                db.query(StatusEvent)
                .filter(
                    StatusEvent.device_id == device.id,
                    StatusEvent.new_state == DeviceState.DOWN,
                    StatusEvent.started_at >= window_start,
                )
                .count()
            )
            if down_count < FLAP_CYCLES:
                continue

            cooldown_start = now - timedelta(hours=FLAP_ALERT_COOLDOWN_HOURS)
            recent_flap_alert = (
                db.query(Alert)
                .filter(Alert.device_id == device.id, Alert.type == "FLAPPING", Alert.created_at >= cooldown_start)
                .first()
            )
            if recent_flap_alert:
                continue

            db.add(
                Alert(
                    device_id=device.id, type="FLAPPING", severity=AlertSeverity.WARNING, state=AlertState.OPEN,
                )
            )
            result["flapping"] += 1

        db.commit()

        # --- Disk-full forecast: simple two-point trend over the lookback window ---
        lookback_start = now - timedelta(days=DISK_FORECAST_LOOKBACK_DAYS)
        nvrs = db.query(Device).filter(Device.type == DeviceType.NVR, Device.active.is_(True)).all()
        for nvr in nvrs:
            samples = (
                db.query(CheckResult)
                .filter(
                    CheckResult.device_id == nvr.id,
                    CheckResult.check_type == CheckType.NVR,
                    CheckResult.time >= lookback_start,
                    CheckResult.metrics_jsonb.isnot(None),
                )
                .order_by(CheckResult.time.asc())
                .all()
            )
            points = [
                (s.time, s.metrics_jsonb.get("disk_pct"))
                for s in samples
                if isinstance(s.metrics_jsonb, dict) and s.metrics_jsonb.get("disk_pct") is not None
            ]
            if len(points) < 2:
                continue

            (t0, p0), (t1, p1) = points[0], points[-1]
            days_elapsed = (t1 - t0).total_seconds() / 86400
            if days_elapsed <= 0 or p1 <= p0:
                continue  # flat or decreasing usage - no forecast risk

            slope_per_day = (p1 - p0) / days_elapsed
            days_to_full = (100 - p1) / slope_per_day
            if days_to_full > DISK_FORECAST_WARNING_DAYS:
                continue

            cooldown_start = now - timedelta(hours=24)
            recent_forecast_alert = (
                db.query(Alert)
                .filter(Alert.device_id == nvr.id, Alert.type == "DISK_FORECAST", Alert.created_at >= cooldown_start)
                .first()
            )
            if recent_forecast_alert:
                continue

            db.add(
                Alert(
                    device_id=nvr.id, type="DISK_FORECAST", severity=AlertSeverity.WARNING, state=AlertState.OPEN,
                )
            )
            result["disk_forecast"] += 1

        db.commit()
    finally:
        db.close()
    return result
