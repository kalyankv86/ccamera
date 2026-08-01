from pydantic import BaseModel

from ccms.models.enums import DeviceState


class StatusCounts(BaseModel):
    total: int = 0
    up: int = 0
    degraded: int = 0
    down: int = 0
    maintenance: int = 0
    unknown: int = 0


class GroupedStatusCounts(BaseModel):
    key: str
    counts: StatusCounts


class StatusSummary(BaseModel):
    overall: StatusCounts
    by_building: list[GroupedStatusCounts]


STATE_FIELD = {
    DeviceState.UP: "up",
    DeviceState.DEGRADED: "degraded",
    DeviceState.DOWN: "down",
    DeviceState.MAINTENANCE: "maintenance",
    DeviceState.UNKNOWN: "unknown",
}
