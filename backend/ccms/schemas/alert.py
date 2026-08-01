from datetime import datetime

from pydantic import BaseModel

from ccms.models.enums import AlertSeverity, AlertState


class AlertOut(BaseModel):
    id: int
    device_id: int
    device_name: str
    group_id: str | None
    type: str
    severity: AlertSeverity
    state: AlertState
    created_at: datetime
    acked_by: int | None
    acked_at: datetime | None
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class DeviceHistoryEvent(BaseModel):
    old_state: str
    new_state: str
    cause: str | None
    started_at: datetime
    ended_at: datetime | None
    downtime_seconds: int | None
    suppressed_by_parent: bool

    model_config = {"from_attributes": True}


class DeviceCheckResultOut(BaseModel):
    time: datetime
    check_type: str
    status: str
    latency_ms: float | None
    loss_pct: float | None

    model_config = {"from_attributes": True}


class DeviceHistory(BaseModel):
    status_events: list[DeviceHistoryEvent]
    recent_checks: list[DeviceCheckResultOut]
    uptime_pct_24h: float | None
