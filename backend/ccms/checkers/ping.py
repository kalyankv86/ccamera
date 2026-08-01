import platform
import re
import subprocess

from icmplib import ping as icmp_ping
from icmplib.exceptions import SocketPermissionError

from ccms.checkers.base import BaseChecker, CheckResultData
from ccms.models.device import Device
from ccms.models.enums import CheckStatus, CheckType


class PingChecker(BaseChecker):
    """FR-02: ICMP reachability. 3 echo requests, records min/avg latency and loss%.

    Tries icmplib's unprivileged raw-socket mode first (works out of the box on
    Linux, the SDD's target server OS). macOS denies unprivileged ICMP sockets to
    non-root processes, so on SocketPermissionError we fall back to shelling out
    to the system `ping` binary, which is fine for local dev/demo without sudo.
    """

    check_type = CheckType.PING
    timeout_s = 5.0
    degraded_loss_pct = 50.0

    def run(self, device: Device) -> CheckResultData:
        try:
            host = icmp_ping(device.ip, count=3, timeout=self.timeout_s, privileged=False)
        except SocketPermissionError:
            return self._run_via_subprocess(device)
        except Exception as exc:  # noqa: BLE001 - checker must never raise
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error=str(exc))

        if host.packets_received == 0:
            return CheckResultData(
                check_type=self.check_type,
                status=CheckStatus.FAIL,
                loss_pct=100.0,
                metrics={"packets_sent": host.packets_sent},
            )

        status = CheckStatus.DEGRADED if host.packet_loss * 100 > self.degraded_loss_pct else CheckStatus.OK
        return CheckResultData(
            check_type=self.check_type,
            status=status,
            latency_ms=host.avg_rtt,
            loss_pct=host.packet_loss * 100,
            metrics={"min_rtt": host.min_rtt, "max_rtt": host.max_rtt},
        )

    def _run_via_subprocess(self, device: Device) -> CheckResultData:
        count = 3
        args = (
            ["ping", "-c", str(count), "-W", "2000", device.ip]
            if platform.system() == "Linux"
            else ["ping", "-c", str(count), "-t", "5", device.ip]  # macOS/BSD ping
        )
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=self.timeout_s + 2)
        except Exception as exc:  # noqa: BLE001
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error=str(exc))

        loss_match = re.search(r"([\d.]+)% packet loss", proc.stdout)
        loss_pct = float(loss_match.group(1)) if loss_match else (0.0 if proc.returncode == 0 else 100.0)

        if loss_pct >= 100.0:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, loss_pct=100.0)

        rtt_match = re.search(r"= [\d.]+/([\d.]+)/", proc.stdout)  # min/avg/max/stddev
        avg_rtt = float(rtt_match.group(1)) if rtt_match else None
        status = CheckStatus.DEGRADED if loss_pct > self.degraded_loss_pct else CheckStatus.OK
        return CheckResultData(check_type=self.check_type, status=status, latency_ms=avg_rtt, loss_pct=loss_pct)
