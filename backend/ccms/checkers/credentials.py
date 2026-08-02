"""Shared helper for checkers that need a device's stored credentials.
Opens its own short-lived session rather than requiring callers to thread a
db session through BaseChecker.run(device), keeping the checker interface
simple (SDD 3.2: `run(device) -> CheckResult`)."""

from urllib.parse import quote, urlsplit, urlunsplit

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


def build_authenticated_rtsp_url(device_id: int, rtsp_url: str) -> str:
    """Injects the device's stored (encrypted-at-rest) credentials into an
    otherwise credential-free rtsp_url at check time - NFR-08 requires
    credentials stored encrypted, so rtsp_url in the devices table must never
    contain a plaintext password itself. Special characters in the password
    (a literal '@' is common) are percent-encoded, since an unescaped '@'
    would otherwise be parsed as the userinfo/host delimiter.

    If the URL already has userinfo (e.g. the simulator's credential-less
    URLs, or a device registered with credentials embedded directly), or no
    stored credentials exist, the URL is returned unchanged.
    """
    creds = get_device_credentials(device_id)
    if creds is None:
        return rtsp_url

    parts = urlsplit(rtsp_url)
    if "@" in parts.netloc:
        return rtsp_url  # already has userinfo - don't override

    username, password = creds
    host_and_port = parts.netloc
    userinfo = f"{quote(username, safe='')}:{quote(password, safe='')}"
    new_netloc = f"{userinfo}@{host_and_port}"
    return urlunsplit((parts.scheme, new_netloc, parts.path, parts.query, parts.fragment))
