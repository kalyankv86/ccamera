"""Minimal ONVIF SOAP client: just enough of Device Management (GetDeviceInformation,
GetSystemDateAndTime) to power NvrChecker's real-hardware health probe, with
WS-Security UsernameToken digest auth over HTTPS.

Why hand-rolled instead of onvif-zeep (already a dependency): onvif-zeep's
transport only ever builds http:// URLs. Real NVRs encountered in the field
(confirmed live against production hardware) reject ONVIF over plain HTTP
with an explicit SOAP fault telling the client to use HTTPS, and reject HTTP
Basic auth (401) - they expect WS-Security UsernameToken digest, which is
the actual ONVIF-standard auth mechanism. For 2-3 known operations, a plain
httpx POST with a hand-built envelope is more predictable than fighting a
SOAP/WSDL binding library's transport internals.

TLS note: verify=False throughout - NVRs overwhelmingly use self-signed
certificates on their local HTTPS service, and there is no CA to check
against on an isolated camera VLAN. This is a deliberate, scoped exception,
not a general TLS-verification policy for the app (HTTPS elsewhere, e.g. the
dashboard's own certbot cert, should stay verified).
"""

import base64
import hashlib
import os
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape

import httpx

DEVICE_WSDL_NS = "http://www.onvif.org/ver10/device/wsdl"


class OnvifError(Exception):
    pass


def _ws_security_header(username: str, password: str) -> str:
    nonce = os.urandom(16)
    nonce_b64 = base64.b64encode(nonce).decode()
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Digest is computed over the raw (unescaped) password bytes per the
    # WS-Security UsernameToken Profile spec - only the Username element
    # below is embedded as literal XML text and needs escaping.
    digest = base64.b64encode(hashlib.sha1(nonce + created.encode() + password.encode()).digest()).decode()
    return f"""<Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
             xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
  <UsernameToken>
    <Username>{xml_escape(username)}</Username>
    <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>
    <Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</Nonce>
    <wsu:Created>{created}</wsu:Created>
  </UsernameToken>
</Security>"""


def _envelope(body: str, username: str, password: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Header>{_ws_security_header(username, password)}</s:Header>
  <s:Body>{body}</s:Body>
</s:Envelope>"""


def _post(url: str, body: str, username: str, password: str, timeout: float) -> str:
    envelope = _envelope(body, username, password)
    resp = httpx.post(
        url,
        content=envelope.encode(),
        headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        timeout=timeout,
        verify=False,
    )
    if resp.status_code == 401:
        raise OnvifError("authentication rejected (401) - check device credentials")
    resp.raise_for_status()
    text = resp.text
    if "<s:Fault" in text or ":Fault>" in text:
        reason = re.search(r"<[^>]*Reason[^>]*>.*?<[^>]*Text[^>]*>(.*?)</", text, re.DOTALL)
        raise OnvifError(reason.group(1).strip() if reason else "SOAP fault returned")
    return text


def _tag_text(xml_text: str, tag: str) -> str | None:
    """Namespace-agnostic single-tag extraction - real devices vary prefixes
    (tt:, tds:, no prefix at all) enough that regex-by-local-name is more
    robust here than maintaining an exact namespace map per vendor."""
    match = re.search(rf"<(?:\w+:)?{tag}[^>]*>(.*?)</(?:\w+:)?{tag}>", xml_text, re.DOTALL)
    return match.group(1).strip() if match else None


def get_device_information(base_url: str, username: str, password: str, timeout: float) -> dict:
    body = f'<GetDeviceInformation xmlns="{DEVICE_WSDL_NS}"/>'
    xml_text = _post(f"{base_url}/onvif/device_service", body, username, password, timeout)
    return {
        "manufacturer": _tag_text(xml_text, "Manufacturer"),
        "model": _tag_text(xml_text, "Model"),
        "firmware_version": _tag_text(xml_text, "FirmwareVersion"),
    }


def get_system_date_and_time(base_url: str, username: str, password: str, timeout: float) -> datetime | None:
    """FR-05: NVR clock sync check. Uses UTCDateTime (device-local-time
    devices without correct TZ config would otherwise look drifted)."""
    body = f'<GetSystemDateAndTime xmlns="{DEVICE_WSDL_NS}"/>'
    xml_text = _post(f"{base_url}/onvif/device_service", body, username, password, timeout)
    utc_block = re.search(r"<(?:\w+:)?UTCDateTime>(.*?)</(?:\w+:)?UTCDateTime>", xml_text, re.DOTALL)
    if not utc_block:
        return None
    block = utc_block.group(1)
    year, month, day = (_tag_text(block, t) for t in ("Year", "Month", "Day"))
    hour, minute, second = (_tag_text(block, t) for t in ("Hour", "Minute", "Second"))
    if not all([year, month, day, hour, minute, second]):
        return None
    return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc)
