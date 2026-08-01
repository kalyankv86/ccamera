import httpx

from ccms.config import settings
from ccms.notifications.base import DeliveryResult, NotificationAdapter


class SmsAdapter(NotificationAdapter):
    """Twilio-shaped. Swapping in the real `twilio` SDK later touches only this
    file - is_configured()/send() are the whole contract the rest of the system
    relies on."""

    channel = "sms"

    def is_configured(self) -> bool:
        return bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number)

    def send(self, *, message: str, recipient: str, subject: str | None = None) -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult("SKIPPED_NOT_CONFIGURED", "Twilio credentials not configured")
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
            resp = httpx.post(
                url,
                data={"From": settings.twilio_from_number, "To": recipient, "Body": message},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                timeout=10,
            )
            resp.raise_for_status()
            return DeliveryResult("SENT")
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult("FAILED", str(exc))
