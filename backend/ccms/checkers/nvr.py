"""FR-05 / SDD 3.2.4: NVR health via ONVIF Profile G and/or vendor HTTP API,
normalised into a common model. Unsupported fields are marked unknown rather
than failing the whole check.

The device simulator's fake NVR (simulator/ccms_sim/onvif_fake.py) speaks this
exact normalized JSON shape directly, so it's treated as first-class "vendor":
a device whose Credential-less onvif_url points at http://127.0.0.1:9500/... is
queried with a plain GET instead of a real ONVIF SOAP call. Real Hikvision/Dahua
support can be added as additional branches in _query_vendor without touching
the evaluator/alerting pipeline.
"""

from datetime import datetime, timezone

import httpx

from ccms.checkers.base import BaseChecker, CheckResultData
from ccms.checkers.credentials import get_device_credentials
from ccms.checkers.onvif_client import OnvifError, get_device_information, get_system_date_and_time
from ccms.models.device import Device
from ccms.models.enums import CheckStatus, CheckType

DISK_WARNING_PCT = 90.0
CLOCK_DRIFT_WARNING_S = 60.0


class NvrChecker(BaseChecker):
    check_type = CheckType.NVR
    timeout_s = 10.0

    def run(self, device: Device) -> CheckResultData:
        try:
            normalized = self._query(device)
        except httpx.TimeoutException:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error="timeout")
        except Exception as exc:  # noqa: BLE001
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error=str(exc))

        recording = normalized.get("recording")
        hdd_status = normalized.get("hdd_status", "unknown")
        disk_pct = normalized.get("disk_pct")
        clock_drift_s = normalized.get("clock_drift_s")

        if recording is False:
            return CheckResultData(
                check_type=self.check_type, status=CheckStatus.FAIL, error="RECORDING_DOWN", metrics=normalized
            )
        if hdd_status not in ("ok", "unknown"):
            return CheckResultData(
                check_type=self.check_type, status=CheckStatus.FAIL, error=f"HDD_FAILURE:{hdd_status}", metrics=normalized
            )

        degraded_reasons = []
        if disk_pct is not None and disk_pct >= DISK_WARNING_PCT:
            degraded_reasons.append("DISK_USAGE_HIGH")
        if clock_drift_s is not None and abs(clock_drift_s) > CLOCK_DRIFT_WARNING_S:
            degraded_reasons.append("CLOCK_DRIFT")

        status = CheckStatus.DEGRADED if degraded_reasons else CheckStatus.OK
        metrics = {**normalized, "degraded_reasons": degraded_reasons}
        return CheckResultData(check_type=self.check_type, status=status, metrics=metrics)

    def _query(self, device: Device) -> dict:
        # Simulator vendor: onvif_url is a plain http(s) URL returning the
        # already-normalized JSON shape directly.
        if device.onvif_url and (
            device.onvif_url.startswith("http://127.0.0.1:9500") or device.onvif_url.startswith("http://localhost:9500")
        ):
            resp = httpx.get(device.onvif_url, timeout=self.timeout_s)
            resp.raise_for_status()
            return resp.json()

        return self._query_vendor(device)

    def _query_vendor(self, device: Device) -> dict:
        """Real ONVIF Device Management probe over HTTPS with WS-Security
        digest auth (ccms.checkers.onvif_client) - confirmed live against
        production NVR hardware. Standardises well for device liveness and
        clock drift (FR-05); ONVIF Profile G recording status and HDD/disk
        capacity are NOT standardized well across vendors and are reported
        "unknown" rather than guessed at, per this module's own design intent.
        """
        creds = get_device_credentials(device.id)
        if creds is None:
            raise RuntimeError("no credentials configured for this device")
        username, password = creds

        # device.onvif_url, when set, is the scheme+host[:port] base
        # (e.g. "https://192.168.3.240") - real NVRs encountered so far
        # require HTTPS specifically, so that's the default when unset.
        base_url = (device.onvif_url or f"https://{device.ip}").rstrip("/")

        try:
            info = get_device_information(base_url, username, password, self.timeout_s)
        except OnvifError as exc:
            raise RuntimeError(f"ONVIF auth/device query failed: {exc}") from exc

        clock_drift_s = None
        try:
            device_time = get_system_date_and_time(base_url, username, password, self.timeout_s)
            if device_time is not None:
                clock_drift_s = (device_time - datetime.now(timezone.utc)).total_seconds()
        except OnvifError:
            pass  # clock check is a bonus signal, not required for a healthy result

        return {
            "recording": None,  # ONVIF Profile G Recording Control not implemented - see module docstring
            "hdd_status": "unknown",
            "disk_pct": None,
            "clock_drift_s": clock_drift_s,
            "manufacturer": info.get("manufacturer"),
            "model": info.get("model"),
            "firmware_version": info.get("firmware_version"),
        }
