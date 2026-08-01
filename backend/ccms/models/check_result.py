"""check_results is a native Postgres RANGE-partitioned table (see
alembic/versions/0002_check_results.py). It is not created via
Base.metadata.create_all/autogenerate; this model exists only so the
application can query/insert against it through the ORM.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from ccms.db import Base
from ccms.models.enums import CheckStatus, CheckType


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    check_type: Mapped[CheckType] = mapped_column(SAEnum(CheckType, name="check_type"), nullable=False)
    status: Mapped[CheckStatus] = mapped_column(SAEnum(CheckStatus, name="check_status"), nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Numeric(10, 2))
    loss_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    metrics_jsonb: Mapped[dict | None] = mapped_column(JSON)
    maintenance_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CheckResultDaily(Base):
    """Downsampled aggregate, populated by the nightly retention rollup (NFR-12)."""

    __tablename__ = "check_results_daily"

    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), primary_key=True)
    day: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    check_type: Mapped[CheckType] = mapped_column(SAEnum(CheckType, name="check_type"), primary_key=True)
    samples: Mapped[int] = mapped_column(default=0, nullable=False)
    up_count: Mapped[int] = mapped_column(default=0, nullable=False)
    fail_count: Mapped[int] = mapped_column(default=0, nullable=False)
    degraded_count: Mapped[int] = mapped_column(default=0, nullable=False)
    avg_latency_ms: Mapped[float | None] = mapped_column(Numeric(10, 2))
    avg_loss_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
