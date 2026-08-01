from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ccms.api.deps import client_ip, get_current_user, get_db
from ccms.audit.logger import record_audit
from ccms.auth.rbac import require_role
from ccms.models.alert import Alert
from ccms.models.device import Device
from ccms.models.enums import AlertState, Role
from ccms.schemas.alert import AlertOut

router = APIRouter()


def _to_alert_out(alert: Alert, device_name: str) -> AlertOut:
    return AlertOut(
        id=alert.id, device_id=alert.device_id, device_name=device_name, group_id=alert.group_id,
        type=alert.type, severity=alert.severity, state=alert.state, created_at=alert.created_at,
        acked_by=alert.acked_by, acked_at=alert.acked_at, closed_at=alert.closed_at,
    )


@router.get("", response_model=list[AlertOut])
def list_alerts(
    state: AlertState | None = None,
    device_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AlertOut]:
    query = db.query(Alert, Device.name).join(Device, Alert.device_id == Device.id)

    # FR-13: Technicians see only alerts for devices belonging to their vendor.
    if current_user.role == Role.TECHNICIAN:
        query = query.filter(Device.vendor_id == current_user.vendor_id)

    if state is not None:
        query = query.filter(Alert.state == state)
    if device_id is not None:
        query = query.filter(Alert.device_id == device_id)

    rows = query.order_by(Alert.created_at.desc()).limit(500).all()
    return [_to_alert_out(a, name) for a, name in rows]


@router.post("/{alert_id}/ack", response_model=AlertOut)
def acknowledge_alert(
    alert_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(Role.ADMIN, Role.SECURITY_OFFICER, Role.TECHNICIAN)),
) -> AlertOut:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")

    device = db.get(Device, alert.device_id)
    if current_user.role == Role.TECHNICIAN and device.vendor_id != current_user.vendor_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not assigned to your vendor")

    if alert.state == AlertState.OPEN:
        alert.state = AlertState.ACKED
        alert.acked_by = current_user.id
        alert.acked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)
        record_audit(
            db, user=current_user, action="alert.ack", target_type="alert", target_id=alert.id,
            ip=client_ip(request),
        )

    return _to_alert_out(alert, device.name)
