"""NFR-12 retention rollup + FR-10 scheduled monthly uptime/SLA report,
emailed to management on the 1st of each month for the prior month."""

import calendar
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func

from ccms.celery_app import celery_app
from ccms.db import SessionLocal
from ccms.models.check_result import CheckResult, CheckResultDaily
from ccms.models.enums import Role
from ccms.models.settings import Setting
from ccms.models.user import User
from ccms.notifications.email_adapter import EmailAdapter
from ccms.reports.excel import render_uptime_xlsx
from ccms.reports.pdf import render_uptime_pdf
from ccms.reports.uptime import compute_fleet_uptime

logger = logging.getLogger(__name__)
REPORT_RECIPIENTS_KEY = "monthly_report_recipients"

RAW_RETENTION_DAYS = 90
DAILY_RETENTION_DAYS = 365 * 3


@celery_app.task(name="ccms.reports.tasks.rollup_and_retire")
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


@celery_app.task(name="ccms.reports.tasks.generate_monthly_report")
def generate_monthly_report() -> None:
    """FR-10: scheduled monthly SLA report, PDF+Excel attached, emailed to
    management for the previous calendar month. Recipients: the `settings`
    row at REPORT_RECIPIENTS_KEY (list[str]) if set, else all active Admins."""
    db = SessionLocal()
    try:
        today = date.today()
        last_day_prev_month = today.replace(day=1) - timedelta(days=1)
        period_start = datetime(
            last_day_prev_month.year, last_day_prev_month.month, 1, tzinfo=timezone.utc
        )
        days_in_month = calendar.monthrange(last_day_prev_month.year, last_day_prev_month.month)[1]
        period_end = period_start + timedelta(days=days_in_month)

        rows = compute_fleet_uptime(db, period_start, period_end)
        if not rows:
            logger.info("generate_monthly_report: no active devices, skipping")
            return

        pdf_bytes = render_uptime_pdf(rows, period_start, period_end)
        xlsx_bytes = render_uptime_xlsx(rows)

        recipients_setting = db.get(Setting, REPORT_RECIPIENTS_KEY)
        recipients = recipients_setting.value_jsonb if recipients_setting else None
        if not recipients:
            recipients = [u.email for u in db.query(User).filter(User.role == Role.ADMIN, User.active.is_(True))]

        subject = f"[CCMS] Monthly Uptime/SLA Report - {period_start:%B %Y}"
        body = (
            f"Attached: uptime/SLA report for {period_start:%B %Y} covering {len(rows)} device(s).\n"
            f"Fleet average uptime: {sum(r.uptime_pct for r in rows) / len(rows):.2f}%"
        )
        adapter = EmailAdapter()
        for recipient in recipients:
            adapter.send(
                message=body, recipient=recipient, subject=subject,
                attachments=[
                    (f"ccms_uptime_{period_start:%Y%m}.pdf", pdf_bytes, "pdf"),
                    (f"ccms_uptime_{period_start:%Y%m}.xlsx", xlsx_bytes, "vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ],
            )
        logger.info("generate_monthly_report: sent to %d recipient(s)", len(recipients))
    finally:
        db.close()
