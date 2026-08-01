"""FR-15 (Could-have): switch port oper-status / PoE draw via SNMP, so root
cause (switch/port failure vs camera failure) can be identified (SDD 3.2.5).
Only exercised against simulator/ccms_sim/snmp_fake.py in this build - no
physical managed switch is available."""

import asyncio

from ccms.checkers.base import BaseChecker, CheckResultData
from ccms.models.device import Device
from ccms.models.enums import CheckStatus, CheckType

IF_OPER_STATUS_OID = "1.3.6.1.2.1.2.2.1.8"  # ifOperStatus, appended with .<ifIndex>


class SnmpChecker(BaseChecker):
    check_type = CheckType.SNMP
    timeout_s = 5.0
    community = "public"

    def run(self, device: Device) -> CheckResultData:
        if not device.channel_no:
            return CheckResultData(
                check_type=self.check_type, status=CheckStatus.ERROR, error="no switch port (channel_no) configured"
            )
        try:
            oper_status = asyncio.run(self._get_oper_status(device.ip, device.channel_no))
        except Exception as exc:  # noqa: BLE001
            return CheckResultData(check_type=self.check_type, status=CheckStatus.ERROR, error=str(exc))

        if oper_status is None:
            return CheckResultData(check_type=self.check_type, status=CheckStatus.FAIL, error="no SNMP response")
        # ifOperStatus: 1=up, 2=down, 3=testing, ...
        if oper_status != 1:
            return CheckResultData(
                check_type=self.check_type, status=CheckStatus.FAIL, error="PORT_DOWN",
                metrics={"if_oper_status": oper_status, "port": device.channel_no},
            )
        return CheckResultData(
            check_type=self.check_type, status=CheckStatus.OK,
            metrics={"if_oper_status": oper_status, "port": device.channel_no},
        )

    async def _get_oper_status(self, ip: str, port_index: int) -> int | None:
        from pysnmp.hlapi.v3arch.asyncio import (
            CommunityData,
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            get_cmd,
        )

        error_indication, error_status, _error_index, var_binds = await get_cmd(
            SnmpEngine(),
            CommunityData(self.community, mpModel=1),
            await UdpTransportTarget.create((ip, 161), timeout=self.timeout_s, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity(f"{IF_OPER_STATUS_OID}.{port_index}")),
        )
        if error_indication or error_status:
            return None
        for _name, value in var_binds:
            return int(value)
        return None
