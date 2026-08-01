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

import httpx

from ccms.checkers.base import BaseChecker, CheckResultData
from ccms.models.device import Device
from ccms.models.enums import CheckStatus, CheckType

DISK_WARNING_PCT = 90.0
CLOCK_DRIFT_WARNING_S = 60.0


class NvrChecker(BaseChecker):
    check_type = CheckType.NVR
    timeout_s = 10.0

    def run(self, device: Device) -> CheckResultData:
        if not device.onvif_url:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error="no onvif_url configured")

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
        if device.onvif_url.startswith("http://127.0.0.1:9500") or device.onvif_url.startswith("http://localhost:9500"):
            resp = httpx.get(device.onvif_url, timeout=self.timeout_s)
            resp.raise_for_status()
            return resp.json()

        return self._query_vendor(device)

    def _query_vendor(self, device: Device) -> dict:
        """Real ONVIF Profile G / vendor HTTP API integration point.

        Not exercised in this build (no physical NVR available) - wire in
        onvif-zeep (ONVIF Profile G GetRecordingSummary/GetStorageConfiguration)
        or vendor-specific ISAPI/HTTP calls here, normalizing their response into
        the same {recording, hdd_status, disk_pct, clock_drift_s} shape the
        simulator already produces.
        """
        raise NotImplementedError(f"no real ONVIF/vendor adapter wired for {device.make or 'unknown vendor'}")
