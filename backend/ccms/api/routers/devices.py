import csv
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ccms.api.deps import client_ip, get_current_user, get_current_user_flexible, get_db
from ccms.audit.logger import record_audit
from ccms.auth.crypto import encrypt_secret
from ccms.auth.rbac import require_role
from ccms.checkers.credentials import build_authenticated_rtsp_url
from ccms.live import mediamtx_client
from ccms.models.check_result import CheckResult
from ccms.models.device import Credential, Device
from ccms.models.enums import DeviceState, DeviceType, Role
from ccms.models.status_event import StatusEvent
from ccms.schemas.alert import DeviceCheckResultOut, DeviceHistory, DeviceHistoryEvent
from ccms.schemas.device import DeviceCreate, DeviceOut, DeviceUpdate

router = APIRouter()

_SNAPSHOT_DIR = Path(__file__).resolve().parents[4] / "data" / "snapshots"


def _apply_credentials(db: Session, device: Device, username: str | None, password: str | None) -> None:
    if username is None and password is None:
        return
    cred = db.query(Credential).filter(Credential.device_id == device.id).first()
    if cred is None:
        cred = Credential(device_id=device.id)
        db.add(cred)
    if username is not None:
        cred.username = username
    if password is not None:
        cred.secret_encrypted = encrypt_secret(password)


def _sync_live_view(device: Device) -> None:
    """Registers/updates this camera's on-demand HLS relay path in mediamtx
    (live view, see ccms.live.mediamtx_client) after the device row and its
    credentials are committed - needs a committed row since credential
    lookup happens in a separate DB session."""
    if device.type != DeviceType.CAMERA or not device.rtsp_url or not device.active:
        return
    url = build_authenticated_rtsp_url(device.id, device.rtsp_url)
    mediamtx_client.register_path(device.id, url)


@router.get("", response_model=list[DeviceOut])
def list_devices(
    building: str | None = None,
    zone: str | None = None,
    active: bool | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[Device]:
    query = db.query(Device)
    if building:
        query = query.filter(Device.building == building)
    if zone:
        query = query.filter(Device.zone == zone)
    if active is not None:
        query = query.filter(Device.active == active)
    return query.order_by(Device.id).all()


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(Role.ADMIN)),
) -> Device:
    data = payload.model_dump(exclude={"credential_username", "credential_password"})
    device = Device(**data)
    db.add(device)
    db.flush()  # assign device.id before writing credentials
    _apply_credentials(db, device, payload.credential_username, payload.credential_password)
    db.commit()
    db.refresh(device)
    _sync_live_view(device)
    record_audit(
        db, user=current_user, action="device.create", target_type="device", target_id=device.id,
        detail={"name": device.name, "ip": device.ip}, ip=client_ip(request),
    )
    return device


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.put("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(Role.ADMIN)),
) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    data = payload.model_dump(exclude={"credential_username", "credential_password"}, exclude_unset=True)
    for field, value in data.items():
        setattr(device, field, value)
    _apply_credentials(db, device, payload.credential_username, payload.credential_password)
    db.commit()
    db.refresh(device)
    _sync_live_view(device)
    record_audit(
        db, user=current_user, action="device.update", target_type="device", target_id=device.id,
        detail=data, ip=client_ip(request),
    )
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_device(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(Role.ADMIN)),
) -> None:
    """Deactivate (soft-delete) rather than hard-delete, preserving history (SRS FR-01)."""
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    device.active = False
    db.commit()
    mediamtx_client.remove_path(device.id)
    record_audit(
        db, user=current_user, action="device.deactivate", target_type="device", target_id=device.id,
        ip=client_ip(request),
    )


@router.post("/import", response_model=list[DeviceOut])
async def bulk_import(
    file: UploadFile,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(Role.ADMIN)),
) -> list[Device]:
    """CSV bulk import (FR-01). Expected columns match DeviceCreate field names."""
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    created: list[Device] = []
    for row in reader:
        row = {k: v for k, v in row.items() if v not in (None, "")}
        try:
            payload = DeviceCreate(**row)
        except Exception as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Row {row!r}: {exc}") from exc
        data = payload.model_dump(exclude={"credential_username", "credential_password"})
        device = Device(**data)
        db.add(device)
        db.flush()
        _apply_credentials(db, device, payload.credential_username, payload.credential_password)
        created.append(device)
    db.commit()
    for device in created:
        db.refresh(device)
        _sync_live_view(device)
    record_audit(
        db, user=current_user, action="device.bulk_import", detail={"count": len(created)}, ip=client_ip(request),
    )
    return created


@router.get("/{device_id}/history", response_model=DeviceHistory)
def device_history(
    device_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
) -> DeviceHistory:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")

    events = (
        db.query(StatusEvent)
        .filter(StatusEvent.device_id == device_id)
        .order_by(StatusEvent.started_at.desc())
        .limit(100)
        .all()
    )
    checks = (
        db.query(CheckResult)
        .filter(CheckResult.device_id == device_id)
        .order_by(CheckResult.time.desc())
        .limit(200)
        .all()
    )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    downtime = (
        db.query(StatusEvent)
        .filter(
            StatusEvent.device_id == device_id,
            StatusEvent.new_state == DeviceState.DOWN,
            StatusEvent.started_at >= cutoff,
            StatusEvent.suppressed_by_parent.is_(False),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    downtime_seconds = sum(
        (e.downtime_seconds if e.downtime_seconds is not None else int((now - e.started_at).total_seconds()))
        for e in downtime
    )
    uptime_pct = max(0.0, 100.0 - (downtime_seconds / (24 * 3600)) * 100.0)

    return DeviceHistory(
        status_events=[DeviceHistoryEvent.model_validate(e) for e in events],
        recent_checks=[DeviceCheckResultOut.model_validate(c) for c in checks],
        uptime_pct_24h=round(uptime_pct, 2),
    )


@router.get("/{device_id}/snapshot")
def device_snapshot(device_id: int, current_user=Depends(get_current_user_flexible)) -> FileResponse:
    """FR-09/SDD 5: latest captured frame (written by ImageChecker, FR-04).
    Officer+ per SDD 5. Uses get_current_user_flexible (header or ?token=)
    because the dashboard loads this via a plain <img> tag, which can't
    attach an Authorization header."""
    if current_user.role not in (Role.SECURITY_OFFICER, Role.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    path = _SNAPSHOT_DIR / f"device_{device_id}_latest.jpg"
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No snapshot available for this device yet")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{device_id}/live")
def device_live(device_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> dict:
    """Live view (HLS, relayed on-demand through mediamtx - see ccms.live).
    Not video recording/playback (explicitly out of Phase-1 scope) - this is
    a real-time "confirm the camera is actually showing what it should"
    view, distinct from the periodic /snapshot still image. Viewer+ (same
    level as the rest of the dashboard) since the stream itself carries no
    credential material - mediamtx holds the camera's decrypted credentials
    server-side and the client only ever sees the relayed HLS path."""
    device = db.get(Device, device_id)
    if not device or device.type != DeviceType.CAMERA:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Camera not found")
    if not device.rtsp_url:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="No rtsp_url configured for this camera")
    return {"hls_url": mediamtx_client.hls_url_for(device_id)}
