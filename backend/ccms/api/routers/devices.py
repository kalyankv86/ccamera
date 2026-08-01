import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from ccms.api.deps import client_ip, get_current_user, get_db
from ccms.audit.logger import record_audit
from ccms.auth.crypto import encrypt_secret
from ccms.auth.rbac import require_role
from ccms.models.device import Credential, Device
from ccms.models.enums import Role
from ccms.schemas.device import DeviceCreate, DeviceOut, DeviceUpdate

router = APIRouter()


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
    record_audit(
        db, user=current_user, action="device.bulk_import", detail={"count": len(created)}, ip=client_ip(request),
    )
    return created
