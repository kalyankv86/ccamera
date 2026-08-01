"""SDD 3.4: events arriving within a 60-second window sharing a common parent
(NVR or switch) are merged into one grouped alert instead of one per camera."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ccms.models.alert import Alert
from ccms.models.device import Device

STORM_WINDOW_SECONDS = 60


def group_id_for(db: Session, device: Device) -> str:
    """Returns an existing group_id if a sibling device (same parent_nvr_id) went
    DOWN within the last STORM_WINDOW_SECONDS, else mints a new one."""
    if device.parent_nvr_id is None:
        return str(uuid.uuid4())

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STORM_WINDOW_SECONDS)
    sibling_alert = (
        db.query(Alert)
        .join(Device, Alert.device_id == Device.id)
        .filter(
            Device.parent_nvr_id == device.parent_nvr_id,
            Alert.created_at >= cutoff,
            Alert.group_id.isnot(None),
        )
        .order_by(Alert.created_at.desc())
        .first()
    )
    return sibling_alert.group_id if sibling_alert else str(uuid.uuid4())
