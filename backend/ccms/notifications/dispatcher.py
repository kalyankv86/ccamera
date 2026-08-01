"""SDD 3.5: Celery task that picks the adapter by channel, retries with
exponential backoff (max 5 attempts), and writes exactly one notification_log
row per attempt regardless of outcome - this is how delivery is provable even
for the no-op channels, and how NFR-06 (queue-and-flush-on-restore) works: a
FAILED SMTP send simply retries via Celery's own retry/backoff mechanism."""

from datetime import datetime, timezone

from ccms.celery_app import celery_app
from ccms.db import SessionLocal
from ccms.models.notification import NotificationLog
from ccms.models.enums import NotificationChannel, NotificationStatus
from ccms.notifications.email_adapter import EmailAdapter
from ccms.notifications.sms_adapter import SmsAdapter
from ccms.notifications.whatsapp_adapter import WhatsAppAdapter

_ADAPTERS = {
    NotificationChannel.EMAIL: EmailAdapter(),
    NotificationChannel.SMS: SmsAdapter(),
    NotificationChannel.WHATSAPP: WhatsAppAdapter(),
}

MAX_ATTEMPTS = 5


@celery_app.task(
    name="ccms.notifications.dispatcher.send_notification",
    bind=True,
    max_retries=MAX_ATTEMPTS,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_notification(self, alert_id: int, channel: str, recipient: str, subject: str, message: str) -> None:
    db = SessionLocal()
    try:
        chan = NotificationChannel(channel)
        adapter = _ADAPTERS[chan]
        log = NotificationLog(alert_id=alert_id, channel=chan, recipient=recipient, attempts=self.request.retries + 1)

        result = adapter.send(message=message, recipient=recipient, subject=subject)

        if result.status == "SENT":
            log.status = NotificationStatus.SENT
            log.delivered_at = datetime.now(timezone.utc)
        elif result.status == "SKIPPED_NOT_CONFIGURED":
            log.status = NotificationStatus.SKIPPED_NOT_CONFIGURED
            log.last_error = result.detail
        else:
            log.status = NotificationStatus.FAILED
            log.last_error = result.detail

        db.add(log)
        db.commit()

        if result.status == "FAILED" and self.request.retries < MAX_ATTEMPTS:
            raise self.retry(exc=RuntimeError(result.detail or "delivery failed"))
    finally:
        db.close()
