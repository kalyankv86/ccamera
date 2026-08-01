from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ccms.db import Base
from ccms.models.enums import DeviceState


class StatusEvent(Base):
    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    old_state: Mapped[DeviceState] = mapped_column(SAEnum(DeviceState, name="device_state"), nullable=False)
    new_state: Mapped[DeviceState] = mapped_column(SAEnum(DeviceState, name="device_state"), nullable=False)
    cause: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    downtime_seconds: Mapped[int | None] = mapped_column(Integer)
    suppressed_by_parent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
