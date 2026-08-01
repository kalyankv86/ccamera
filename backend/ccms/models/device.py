from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ccms.db import Base
from ccms.models.enums import Criticality, DeviceState, DeviceType


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType, name="device_type"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    make: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))

    ip: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rtsp_url: Mapped[str | None] = mapped_column(String(500))
    onvif_url: Mapped[str | None] = mapped_column(String(500))

    parent_nvr_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    channel_no: Mapped[int | None] = mapped_column(Integer)

    building: Mapped[str | None] = mapped_column(String(200), index=True)
    zone: Mapped[str | None] = mapped_column(String(200), index=True)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)

    installation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), index=True)
    criticality: Mapped[Criticality] = mapped_column(
        SAEnum(Criticality, name="criticality"), default=Criticality.NORMAL, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Current cached state (denormalized for fast dashboard reads; source of truth is status_events)
    current_state: Mapped[DeviceState] = mapped_column(
        SAEnum(DeviceState, name="device_state"), default=DeviceState.UNKNOWN, nullable=False
    )

    # Per-check configurable intervals (FR-02/FR-03), seconds
    ping_interval_s: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    rtsp_interval_s: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    nvr_interval_s: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    image_interval_s: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    # Scheduler due-timestamps (SDD 3.1 dispatcher reads these instead of a separate schedule table)
    next_ping_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_rtsp_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_nvr_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_image_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(200))
    # AES-256-GCM ciphertext, base64, per NFR-08 (never returned by the API)
    secret_encrypted: Mapped[str | None] = mapped_column(String(1000))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
