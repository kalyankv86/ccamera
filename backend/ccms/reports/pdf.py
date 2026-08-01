import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ccms.reports.uptime import DeviceUptime


def render_uptime_pdf(rows: list[DeviceUptime], start: datetime, end: datetime) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("CCMS Uptime / SLA Report", styles["Title"]),
        Paragraph(f"{start:%Y-%m-%d} to {end:%Y-%m-%d}", styles["Normal"]),
        Spacer(1, 16),
    ]

    data = [["Device", "Building", "Vendor", "Uptime %", "Downtime", "SLA Target", "Met?"]]
    for r in rows:
        downtime_str = f"{r.downtime_seconds // 3600}h {(r.downtime_seconds % 3600) // 60}m"
        data.append(
            [
                r.device_name, r.building or "-", r.vendor_name or "-", f"{r.uptime_pct:.2f}%",
                downtime_str, f"{r.sla_target_pct:.1f}%" if r.sla_target_pct is not None else "-",
                ("Yes" if r.sla_met else "No") if r.sla_met is not None else "-",
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f6fed")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6f8")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()
