"""FR-10 / SDD 4.3: Uptime % for a device over a period =
(period_seconds - SUM(downtime_seconds of DOWN events overlapping the period,
excluding maintenance and suppressed-by-parent time)) / period_seconds * 100.
Building/NVR/vendor uptime are averages weighted equally per device. SLA
compliance compares device uptime against vendors.sla_target_pct.

Maintenance-window downtime is already excluded "for free": the evaluator
(evaluator/service.py) transitions a device straight to MAINTENANCE state
during an active window instead of running it through the normal DOWN
debounce path, so no DOWN status_event is ever created for that time.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ccms.models.device import Device
from ccms.models.enums import DeviceState
from ccms.models.status_event import StatusEvent
from ccms.models.vendor import Vendor


@dataclass
class DeviceUptime:
    device_id: int
    device_name: str
    building: str | None
    vendor_id: int | None
    vendor_name: str | None
    uptime_pct: float
    downtime_seconds: int
    sla_target_pct: float | None
    sla_met: bool | None


def _overlap_seconds(event: StatusEvent, start: datetime, end: datetime, now: datetime) -> float:
    event_start = event.started_at
    if event_start.tzinfo is None:
        event_start = event_start.replace(tzinfo=timezone.utc)
    event_end = event.ended_at or now
    if event_end.tzinfo is None:
        event_end = event_end.replace(tzinfo=timezone.utc)

    overlap_start = max(event_start, start)
    overlap_end = min(event_end, end)
    return max(0.0, (overlap_end - overlap_start).total_seconds())


def compute_device_uptime(db: Session, device: Device, start: datetime, end: datetime) -> DeviceUptime:
    now = datetime.now(timezone.utc)
    period_seconds = (end - start).total_seconds()

    down_events = (
        db.query(StatusEvent)
        .filter(
            StatusEvent.device_id == device.id,
            StatusEvent.new_state == DeviceState.DOWN,
            StatusEvent.suppressed_by_parent.is_(False),
            StatusEvent.started_at < end,
        )
        .all()
    )
    downtime_seconds = sum(_overlap_seconds(e, start, end, now) for e in down_events)
    uptime_pct = 100.0 if period_seconds <= 0 else max(0.0, 100.0 - (downtime_seconds / period_seconds) * 100.0)

    vendor = db.get(Vendor, device.vendor_id) if device.vendor_id else None
    sla_target = float(vendor.sla_target_pct) if vendor else None

    return DeviceUptime(
        device_id=device.id,
        device_name=device.name,
        building=device.building,
        vendor_id=device.vendor_id,
        vendor_name=vendor.name if vendor else None,
        uptime_pct=round(uptime_pct, 3),
        downtime_seconds=int(downtime_seconds),
        sla_target_pct=sla_target,
        sla_met=(uptime_pct >= sla_target) if sla_target is not None else None,
    )


def compute_fleet_uptime(db: Session, start: datetime, end: datetime, device_ids: list[int] | None = None) -> list[DeviceUptime]:
    query = db.query(Device).filter(Device.active.is_(True))
    if device_ids:
        query = query.filter(Device.id.in_(device_ids))
    devices = query.all()
    return [compute_device_uptime(db, d, start, end) for d in devices]


def group_average(rows: list[DeviceUptime], key: str) -> dict[str, float]:
    """Building/vendor uptime = simple average across devices in the group
    (equally weighted per device, per SDD 4.3), not weighted by downtime."""
    buckets: dict[str, list[float]] = {}
    for row in rows:
        group_key = getattr(row, key) or "(unassigned)"
        buckets.setdefault(group_key, []).append(row.uptime_pct)
    return {k: round(sum(v) / len(v), 3) for k, v in buckets.items()}
