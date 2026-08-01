import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ccms.config import settings
from ccms.notifications.base import DeliveryResult, NotificationAdapter


class EmailAdapter(NotificationAdapter):
    channel = "email"

    def is_configured(self) -> bool:
        return bool(settings.smtp_host)

    def send(
        self,
        *,
        message: str,
        recipient: str,
        subject: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> DeliveryResult:
        """attachments: list of (filename, content, mime_subtype), e.g.
        ("report.pdf", pdf_bytes, "pdf") - used by the monthly report task,
        not by alert notifications."""
        if not self.is_configured():
            return DeliveryResult("SKIPPED_NOT_CONFIGURED", "SMTP host not configured")
        try:
            if attachments:
                msg = MIMEMultipart()
                msg.attach(MIMEText(message))
                for filename, content, subtype in attachments:
                    part = MIMEApplication(content, _subtype=subtype)
                    part.add_header("Content-Disposition", "attachment", filename=filename)
                    msg.attach(part)
            else:
                msg = MIMEText(message)

            msg["Subject"] = subject or "CCMS Alert"
            msg["From"] = settings.smtp_from
            msg["To"] = recipient
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_pass)
                smtp.sendmail(settings.smtp_from, [recipient], msg.as_string())
            return DeliveryResult("SENT")
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult("FAILED", str(exc))
