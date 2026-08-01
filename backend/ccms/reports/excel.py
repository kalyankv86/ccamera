import io

from openpyxl import Workbook
from openpyxl.styles import Font

from ccms.reports.uptime import DeviceUptime


def render_uptime_xlsx(rows: list[DeviceUptime]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Uptime"

    headers = ["Device", "Building", "Vendor", "Uptime %", "Downtime (s)", "SLA Target %", "SLA Met"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r in rows:
        ws.append(
            [
                r.device_name, r.building or "", r.vendor_name or "", r.uptime_pct, r.downtime_seconds,
                r.sla_target_pct if r.sla_target_pct is not None else "",
                "" if r.sla_met is None else ("Yes" if r.sla_met else "No"),
            ]
        )

    for column_cells in ws.columns:
        length = max(len(str(c.value)) for c in column_cells if c.value is not None) if any(c.value for c in column_cells) else 10
        ws.column_dimensions[column_cells[0].column_letter].width = min(40, length + 2)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
