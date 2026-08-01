"""NFR-12 retention rollup (implemented now) + FR-10 scheduled monthly report
(full PDF/Excel rendering lands in M9 - reports/uptime.py, reports/pdf.py,
reports/excel.py). Both are registered in celery_app.beat_schedule so they must
exist and be safe no-ops until M9 fleshes generate_monthly_report out."""

import logging
from datetime import date, datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import func

from ccms.db import SessionLocal
from ccms.models.check_result import CheckResult, CheckResultDaily

logger = logging.getLogger(__name__)

RAW_RETENTION_DAYS = 90
DAILY_RETENTION_DAYS = 365 * 3


@shared_task(name="ccms.reports.tasks.rollup_and_retire")
def rollup_and_retire() -> None:
    """Aggregates check_results partitions wholly older than 90 days into
    check_results_daily, then drops the raw partition (NFR-12)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RAW_RETENTION_DAYS)
    db = SessionLocal()
    try:
        rows = (
            db.query(
                CheckResult.device_id,
                func.date_trunc("day", CheckResult.time).label("day"),
                CheckResult.check_type,
                func.count().label("samples"),
                func.count().filter(CheckResult.status == "OK").label("up_count"),
                func.count().filter(CheckResult.status == "FAIL").label("fail_count"),
                func.count().filter(CheckResult.status == "DEGRADED").label("degraded_count"),
                func.avg(CheckResult.latency_ms).label("avg_latency_ms"),
                func.avg(CheckResult.loss_pct).label("avg_loss_pct"),
            )
            .filter(CheckResult.time < cutoff)
            .group_by(CheckResult.device_id, func.date_trunc("day", CheckResult.time), CheckResult.check_type)
            .all()
        )
        for row in rows:
            existing = db.get(CheckResultDaily, (row.device_id, row.day, row.check_type))
            if existing is None:
                db.add(
                    CheckResultDaily(
                        device_id=row.device_id, day=row.day, check_type=row.check_type,
                        samples=row.samples, up_count=row.up_count, fail_count=row.fail_count,
                        degraded_count=row.degraded_count, avg_latency_ms=row.avg_latency_ms,
                        avg_loss_pct=row.avg_loss_pct,
                    )
                )
        db.commit()

        db.execute(CheckResult.__table__.delete().where(CheckResult.time < cutoff))
        db.commit()

        daily_cutoff = datetime.now(timezone.utc) - timedelta(days=DAILY_RETENTION_DAYS)
        db.execute(CheckResultDaily.__table__.delete().where(CheckResultDaily.day < daily_cutoff))
        db.commit()
    finally:
        db.close()


@shared_task(name="ccms.reports.tasks.generate_monthly_report")
def generate_monthly_report() -> None:
    """FR-10: scheduled monthly SLA report emailed to management. Full
    implementation (reports/uptime.py + pdf.py/excel.py + email) lands in M9."""
    logger.info("generate_monthly_report: not yet implemented (M9)")
