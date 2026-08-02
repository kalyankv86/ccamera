"""Shared helper for checkers that need a device's stored credentials
(NvrChecker today; RTSP/ONVIF-authenticated stream checks could reuse this
later). Opens its own short-lived session rather than requiring callers to
thread a db session through BaseChecker.run(device), keeping the checker
interface simple (SDD 3.2: `run(device) -> CheckResult`)."""

from ccms.auth.crypto import decrypt_secret
from ccms.db import SessionLocal
from ccms.models.device import Credential


def get_device_credentials(device_id: int) -> tuple[str, str] | None:
    db = SessionLocal()
    try:
        cred = db.query(Credential).filter(Credential.device_id == device_id).first()
        if not cred or not cred.username or not cred.secret_encrypted:
            return None
        return cred.username, decrypt_secret(cred.secret_encrypted)
    finally:
        db.close()
