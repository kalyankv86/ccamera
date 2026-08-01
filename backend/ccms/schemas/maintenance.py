from datetime import datetime

from pydantic import BaseModel

from ccms.models.enums import MaintenanceScope


class MaintenanceWindowCreate(BaseModel):
    scope_type: MaintenanceScope
    scope_id: int | None = None  # device id (DEVICE) or parent_nvr_id (GROUP)
    scope_building: str | None = None  # for BUILDING scope
    starts_at: datetime
    ends_at: datetime
    rrule: str | None = None
    reason: str | None = None


class MaintenanceWindowOut(BaseModel):
    id: int
    scope_type: MaintenanceScope
    scope_id: int | None
    scope_building: str | None
    starts_at: datetime
    ends_at: datetime
    rrule: str | None
    reason: str | None
    created_by: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
