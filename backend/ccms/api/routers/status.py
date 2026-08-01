from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import func
from sqlalchemy.orm import Session

from ccms.api.deps import get_current_user, get_db
from ccms.models.device import Device
from ccms.realtime import subscribe_status_changes
from ccms.schemas.status import STATE_FIELD, GroupedStatusCounts, StatusCounts, StatusSummary

router = APIRouter()


@router.get("/summary", response_model=StatusSummary)
def status_summary(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> StatusSummary:
    overall_rows = (
        db.query(Device.current_state, func.count())
        .filter(Device.active.is_(True))
        .group_by(Device.current_state)
        .all()
    )
    overall = StatusCounts()
    for state, n in overall_rows:
        field = STATE_FIELD.get(state)
        if field:
            setattr(overall, field, getattr(overall, field) + n)
        overall.total += n

    by_building_rows = (
        db.query(Device.building, Device.current_state, func.count())
        .filter(Device.active.is_(True))
        .group_by(Device.building, Device.current_state)
        .all()
    )
    grouped: dict[str, StatusCounts] = {}
    for building, state, n in by_building_rows:
        key = building or "(unassigned)"
        counts = grouped.setdefault(key, StatusCounts())
        field = STATE_FIELD.get(state)
        if field:
            setattr(counts, field, getattr(counts, field) + n)
        counts.total += n

    return StatusSummary(
        overall=overall,
        by_building=[GroupedStatusCounts(key=k, counts=v) for k, v in sorted(grouped.items())],
    )


@router.websocket("/live")
async def status_live(websocket: WebSocket) -> None:
    """SDD 3.7: pushes {device_id, old_state, new_state} as they happen.
    Auth: the dashboard passes its JWT as a query param (WebSocket handshakes
    can't carry an Authorization header from a browser client)."""
    from ccms.auth.security import decode_access_token

    token = websocket.query_params.get("token")
    if not token or not decode_access_token(token):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        async for message in subscribe_status_changes():
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
