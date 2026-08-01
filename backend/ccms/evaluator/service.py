"""SDD 3.3: runs after each check result is persisted. Maintains per-device
debounce counters (in-process dict; fine at 300-device scale for one evaluator
process) and writes status_events on transitions, with downtime computation and
root-cause suppression when a parent NVR/switch is already DOWN."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ccms.evaluator.state_machine import DebounceCounters, next_state
from ccms.models.device import Device
from ccms.models.enums import CheckStatus, DeviceState
from ccms.models.status_event import StatusEvent

_counters: dict[int, DebounceCounters] = {}


def _counters_for(device_id: int) -> DebounceCounters:
    return _counters.setdefault(device_id, DebounceCounters())


def evaluate(db: Session, device: Device, check_status: CheckStatus, *, maintenance_flag: bool, cause: str | None) -> StatusEvent | None:
    """Returns the newly written StatusEvent on a transition, else None."""
    if maintenance_flag:
        if device.current_state != DeviceState.MAINTENANCE:
            return _transition(db, device, DeviceState.MAINTENANCE, cause="maintenance window active", suppressed=False)
        return None

    if device.current_state == DeviceState.MAINTENANCE:
        device.current_state = DeviceState.UNKNOWN  # re-enter normal evaluation once window ends
        _counters.pop(device.id, None)

    counters = _counters_for(device.id)
    new_state, counters = next_state(device.current_state, counters, check_status)
    _counters[device.id] = counters

    if new_state == device.current_state:
        return None

    suppressed = _is_suppressed_by_parent(db, device, new_state)
    return _transition(db, device, new_state, cause=cause, suppressed=suppressed)


def _is_suppressed_by_parent(db: Session, device: Device, new_state: DeviceState) -> bool:
    if new_state != DeviceState.DOWN or device.parent_nvr_id is None:
        return False
    parent = db.get(Device, device.parent_nvr_id)
    return bool(parent and parent.current_state == DeviceState.DOWN)


def _transition(db: Session, device: Device, new_state: DeviceState, *, cause: str | None, suppressed: bool) -> StatusEvent:
    now = datetime.now(timezone.utc)
    old_state = device.current_state

    event = StatusEvent(
        device_id=device.id,
        old_state=old_state,
        new_state=new_state,
        cause=cause,
        started_at=now,
        suppressed_by_parent=suppressed,
    )

    if old_state == DeviceState.DOWN and new_state in (DeviceState.UP, DeviceState.DEGRADED):
        last_down = (
            db.query(StatusEvent)
            .filter(StatusEvent.device_id == device.id, StatusEvent.new_state == DeviceState.DOWN)
            .order_by(StatusEvent.started_at.desc())
            .first()
        )
        if last_down:
            last_down.ended_at = now
            last_down.downtime_seconds = int((now - last_down.started_at).total_seconds())

    device.current_state = new_state
    db.add(event)
    db.flush()
    return event
