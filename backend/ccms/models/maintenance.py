from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from ccms.db import Base
from ccms.models.enums import MaintenanceScope


class MaintenanceWindow(Base):
    __tablename__ = "maintenance_windows"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[MaintenanceScope] = mapped_column(
        SAEnum(MaintenanceScope, name="maintenance_scope"), nullable=False
    )
    # DEVICE/GROUP windows reference devices.id (device or parent-NVR id) here.
    scope_id: Mapped[int | None] = mapped_column(Integer)
    # BUILDING windows match Device.building by name instead (buildings aren't a table).
    scope_building: Mapped[str | None] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rrule: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
