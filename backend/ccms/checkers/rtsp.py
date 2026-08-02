import json
import subprocess

from ccms.checkers.base import BaseChecker, CheckResultData
from ccms.checkers.credentials import build_authenticated_rtsp_url
from ccms.models.device import Device
from ccms.models.enums import CheckStatus, CheckType


class RtspChecker(BaseChecker):
    """FR-03: opens the camera's (sub-)stream via ffprobe and verifies at least
    one decodable video frame, per SDD 3.2.2. Distinguishes connection-refused /
    auth-failure / timeout / no-frames error classes via ffprobe's stderr."""

    check_type = CheckType.RTSP
    timeout_s = 10.0

    def run(self, device: Device) -> CheckResultData:
        if not device.rtsp_url:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error="no rtsp_url configured")

        url = build_authenticated_rtsp_url(device.id, device.rtsp_url)

        # No -timeout flag: on ffmpeg <= 4.4 (confirmed live - Ubuntu 22.04's
        # apt package), "-timeout" on the RTSP demuxer is deprecated in a way
        # that implies *listen* (server) mode instead of a client connection
        # timeout, causing every real request to fail with "Unable to open
        # RTSP for listening" / "Cannot assign requested address". The
        # process-level timeout below is protocol-version-agnostic and is
        # the only bound needed here.
        cmd = [
            "ffprobe",
            "-v", "error",
            "-rtsp_transport", "tcp",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height",
            "-of", "json",
            url,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout_s + 3)
        except subprocess.TimeoutExpired:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error="timeout")
        except Exception as exc:  # noqa: BLE001
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error=str(exc))

        stderr = proc.stderr.lower()
        if proc.returncode != 0 or not proc.stdout.strip():
            if "401" in stderr or "unauthorized" in stderr:
                error = "authentication failure"
            elif "connection refused" in stderr:
                error = "connection refused"
            elif "timed out" in stderr or "timeout" in stderr:
                error = "timeout"
            else:
                error = "no-frames"
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error=error)

        try:
            info = json.loads(proc.stdout)
            stream = (info.get("streams") or [{}])[0]
        except (json.JSONDecodeError, IndexError):
            stream = {}

        if not stream:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error="no-frames")

        return CheckResultData(
            check_type=self.check_type,
            status=CheckStatus.OK,
            metrics={
                "codec": stream.get("codec_name"),
                "width": stream.get("width"),
                "height": stream.get("height"),
            },
        )
