"""SDD 3.2: Celery task wrappers around each checker. A checker exception never
crashes the worker - any unhandled error becomes CheckResult(ERROR) here
(SDD 6.4). Each task: runs the checker, writes one check_results row, then
hands off to the state evaluator and (on a transition) the alert engine."""

from datetime import datetime, timezone

from ccms.alerts.engine import handle_transition
from ccms.checkers.base import CheckResultData
from ccms.checkers.image import ImageChecker
from ccms.checkers.nvr import NvrChecker
from ccms.checkers.ping import PingChecker
from ccms.checkers.rtsp import RtspChecker
from ccms.checkers.snmp import SnmpChecker
from ccms.celery_app import celery_app
from ccms.db import SessionLocal
from ccms.evaluator.service import evaluate
from ccms.models.check_result import CheckResult
from ccms.models.device import Device

_CHECKERS = {
    "ping": PingChecker(),
    "rtsp": RtspChecker(),
    "nvr": NvrChecker(),
    "image": ImageChecker(),
    "snmp": SnmpChecker(),
}


def _run_and_record(device_id: int, checker_key: str, maintenance_flag: bool) -> None:
    db = SessionLocal()
    try:
        device = db.get(Device, device_id)
        if device is None or not device.active:
            return

        checker = _CHECKERS[checker_key]
        try:
            result: CheckResultData = checker.run(device)
        except Exception as exc:  # noqa: BLE001 - checker contract says never raise, but belt & suspenders
            from ccms.models.enums import CheckStatus

            result = CheckResultData(check_type=checker.check_type, status=CheckStatus.ERROR, error=str(exc))

        # Lock the device row BEFORE inserting check_results, not after:
        # inserting a check_results row (FK -> devices) takes an implicit
        # FOR KEY SHARE lock on the device row as part of the FK check. If two
        # concurrent transactions each insert first and then try to upgrade to
        # FOR UPDATE, Postgres deadlocks (classic KEY SHARE -> UPDATE upgrade
        # deadlock). Locking first means everyone either gets FOR UPDATE
        # cleanly or blocks on initial acquisition - no upgrade, no deadlock.
        #
        # populate_existing() matters here: `device` (above) already loaded
        # this row into the session's identity map, so without it SQLAlchemy
        # would hand back that same Python object with its stale in-memory
        # counter values instead of the fresh, just-unblocked, FOR UPDATE
        # row - silently defeating the whole point of locking.
        locked_device = (
            db.query(Device).filter(Device.id == device_id).populate_existing().with_for_update().one()
        )

        db.add(
            CheckResult(
                time=datetime.now(timezone.utc),
                device_id=device_id,
                check_type=result.check_type,
                status=result.status,
                latency_ms=result.latency_ms,
                loss_pct=result.loss_pct,
                metrics_jsonb={**result.metrics, **({"error": result.error} if result.error else {})},
                maintenance_flag=maintenance_flag,
            )
        )
        db.flush()

        event = evaluate(db, locked_device, result.status, maintenance_flag=maintenance_flag, cause=result.error)
        db.commit()

        if event is not None:
            handle_transition(db, locked_device, event)
    finally:
        db.close()


@celery_app.task(name="ccms.checkers.tasks.run_ping_check")
def run_ping_check(device_id: int, maintenance_flag: bool = False) -> None:
    _run_and_record(device_id, "ping", maintenance_flag)


@celery_app.task(name="ccms.checkers.tasks.run_rtsp_check")
def run_rtsp_check(device_id: int, maintenance_flag: bool = False) -> None:
    _run_and_record(device_id, "rtsp", maintenance_flag)


@celery_app.task(name="ccms.checkers.tasks.run_nvr_check")
def run_nvr_check(device_id: int, maintenance_flag: bool = False) -> None:
    _run_and_record(device_id, "nvr", maintenance_flag)


@celery_app.task(name="ccms.checkers.tasks.run_image_check")
def run_image_check(device_id: int, maintenance_flag: bool = False) -> None:
    _run_and_record(device_id, "image", maintenance_flag)


@celery_app.task(name="ccms.checkers.tasks.run_snmp_check")
def run_snmp_check(device_id: int, maintenance_flag: bool = False) -> None:
    _run_and_record(device_id, "snmp", maintenance_flag)


@celery_app.task(name="ccms.checkers.tasks.ensure_partitions_task")
def ensure_partitions_task() -> None:
    from ccms.scheduler.partitions import ensure_partitions

    ensure_partitions(months_ahead=3)
