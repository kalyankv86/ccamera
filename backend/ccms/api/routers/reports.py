from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ccms.api.deps import client_ip, get_current_user_flexible, get_db
from ccms.audit.logger import record_audit
from ccms.reports.excel import render_uptime_xlsx
from ccms.reports.pdf import render_uptime_pdf
from ccms.reports.uptime import DeviceUptime, compute_fleet_uptime, group_average

router = APIRouter()


@router.get("/uptime")
def uptime_report(
    request: Request,
    date_from: datetime = Query(..., alias="from"),
    date_to: datetime = Query(..., alias="to"),
    format: Literal["json", "pdf", "xlsx"] = "json",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_flexible),
):
    if date_from.tzinfo is None:
        date_from = date_from.replace(tzinfo=timezone.utc)
    if date_to.tzinfo is None:
        date_to = date_to.replace(tzinfo=timezone.utc)

    rows: list[DeviceUptime] = compute_fleet_uptime(db, date_from, date_to)

    record_audit(
        db, user=current_user, action="report.export", detail={"format": format, "from": str(date_from), "to": str(date_to)},
        ip=client_ip(request),
    )

    if format == "pdf":
        content = render_uptime_pdf(rows, date_from, date_to)
        return Response(content=content, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="ccms_uptime_{date_from:%Y%m%d}_{date_to:%Y%m%d}.pdf"'
        })
    if format == "xlsx":
        content = render_uptime_xlsx(rows)
        return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={
            "Content-Disposition": f'attachment; filename="ccms_uptime_{date_from:%Y%m%d}_{date_to:%Y%m%d}.xlsx"'
        })

    return {
        "from": date_from, "to": date_to,
        "devices": [vars(r) for r in rows],
        "by_building": group_average(rows, "building"),
        "by_vendor": group_average(rows, "vendor_name"),
    }
