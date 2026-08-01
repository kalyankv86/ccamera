"""FR-12: maintenance windows. Checks continue during a window, but the
scheduler tags jobs maintenance_flag=true so the evaluator suppresses alerting
and downtime is excluded from SLA computation (SDD 3.1)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ccms.models.device import Device
from ccms.models.enums import MaintenanceScope
from ccms.models.maintenance import MaintenanceWindow


def is_device_in_maintenance(db: Session, device: Device, at: datetime | None = None) -> bool:
    at = at or datetime.now(timezone.utc)
    windows = (
        db.query(MaintenanceWindow)
        .filter(MaintenanceWindow.starts_at <= at, MaintenanceWindow.ends_at >= at)
        .all()
    )
    for window in windows:
        if window.scope_type == MaintenanceScope.CAMPUS:
            return True
        if window.scope_type == MaintenanceScope.DEVICE and window.scope_id == device.id:
            return True
        if window.scope_type == MaintenanceScope.BUILDING and window.scope_building == device.building:
            return True
        if window.scope_type == MaintenanceScope.GROUP and window.scope_id == device.parent_nvr_id:
            return True
    return False
