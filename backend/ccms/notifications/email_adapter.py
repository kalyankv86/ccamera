import shutil
import smtplib
import subprocess
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ccms.config import settings
from ccms.notifications.base import DeliveryResult, NotificationAdapter


class EmailAdapter(NotificationAdapter):
    channel = "email"

    def is_configured(self) -> bool:
        if settings.email_transport == "msmtp":
            return shutil.which(settings.msmtp_binary) is not None
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
            detail = "msmtp binary not found on PATH" if settings.email_transport == "msmtp" else "SMTP host not configured"
            return DeliveryResult("SKIPPED_NOT_CONFIGURED", detail)

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

        if settings.email_transport == "msmtp":
            return self._send_via_msmtp(msg, recipient)
        return self._send_via_smtp(msg, recipient)

    def _send_via_smtp(self, msg, recipient: str) -> DeliveryResult:
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_tls:
                    smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_pass)
                smtp.sendmail(settings.smtp_from, [recipient], msg.as_string())
            return DeliveryResult("SENT")
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult("FAILED", str(exc))

    def _send_via_msmtp(self, msg, recipient: str) -> DeliveryResult:
        """Pipes the message to `msmtp -a <account> <recipient>`, which
        relays via whatever's configured in /etc/msmtprc (or ~/.msmtprc) -
        the standard sendmail-compatible way to send from a server that
        already has a local mail relay set up, rather than the app holding
        SMTP credentials itself."""
        try:
            proc = subprocess.run(
                [settings.msmtp_binary, "-a", settings.msmtp_account, "--", recipient],
                input=msg.as_bytes(),
                capture_output=True,
                timeout=15,
            )
            if proc.returncode != 0:
                return DeliveryResult("FAILED", proc.stderr.decode(errors="replace").strip() or "msmtp exited non-zero")
            return DeliveryResult("SENT")
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult("FAILED", str(exc))
