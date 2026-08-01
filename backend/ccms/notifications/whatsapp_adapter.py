import httpx

from ccms.config import settings
from ccms.notifications.base import DeliveryResult, NotificationAdapter


class WhatsAppAdapter(NotificationAdapter):
    """Generic webhook-shaped adapter: POSTs {to, template, params} with a
    bearer token, matching the shape of most WhatsApp Business API providers
    (Meta Cloud API, Twilio, Gupshup, etc. all accept a thin wrapper like this).
    Swap WHATSAPP_WEBHOOK_URL/API_TOKEN for the institution's chosen provider."""

    channel = "whatsapp"

    def is_configured(self) -> bool:
        return bool(settings.whatsapp_webhook_url and settings.whatsapp_api_token)

    def send(self, *, message: str, recipient: str, subject: str | None = None) -> DeliveryResult:
        if not self.is_configured():
            return DeliveryResult("SKIPPED_NOT_CONFIGURED", "WhatsApp webhook not configured")
        try:
            resp = httpx.post(
                settings.whatsapp_webhook_url,
                json={"to": recipient, "template": "ccms_alert", "params": {"message": message}},
                headers={"Authorization": f"Bearer {settings.whatsapp_api_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            return DeliveryResult("SENT")
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult("FAILED", str(exc))
