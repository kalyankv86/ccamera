from datetime import datetime

from pydantic import BaseModel, Field

from ccms.models.enums import Criticality, DeviceState, DeviceType


class DeviceCreate(BaseModel):
    type: DeviceType
    name: str
    make: str | None = None
    model: str | None = None
    ip: str
    rtsp_url: str | None = None
    onvif_url: str | None = None
    parent_nvr_id: int | None = None
    channel_no: int | None = None
    building: str | None = None
    zone: str | None = None
    lat: float | None = None
    lng: float | None = None
    vendor_id: int | None = None
    criticality: Criticality = Criticality.NORMAL
    ping_interval_s: int = Field(default=60, ge=30, le=300)
    rtsp_interval_s: int = Field(default=300, ge=60, le=1800)
    # optional credentials, encrypted on write, never returned
    credential_username: str | None = None
    credential_password: str | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    make: str | None = None
    model: str | None = None
    ip: str | None = None
    rtsp_url: str | None = None
    onvif_url: str | None = None
    parent_nvr_id: int | None = None
    channel_no: int | None = None
    building: str | None = None
    zone: str | None = None
    lat: float | None = None
    lng: float | None = None
    vendor_id: int | None = None
    criticality: Criticality | None = None
    active: bool | None = None
    ping_interval_s: int | None = None
    rtsp_interval_s: int | None = None
    credential_username: str | None = None
    credential_password: str | None = None


class DeviceOut(BaseModel):
    id: int
    type: DeviceType
    name: str
    make: str | None
    model: str | None
    ip: str
    rtsp_url: str | None
    onvif_url: str | None
    parent_nvr_id: int | None
    channel_no: int | None
    building: str | None
    zone: str | None
    lat: float | None
    lng: float | None
    vendor_id: int | None
    criticality: Criticality
    active: bool
    current_state: DeviceState
    ping_interval_s: int
    rtsp_interval_s: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
