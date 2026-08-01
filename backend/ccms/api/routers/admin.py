from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ccms.api.deps import client_ip, get_db
from ccms.audit.logger import record_audit
from ccms.auth.rbac import require_role
from ccms.auth.security import hash_password
from ccms.models.enums import Role
from ccms.models.maintenance import MaintenanceWindow
from ccms.models.user import User
from ccms.schemas.maintenance import MaintenanceWindowCreate, MaintenanceWindowOut
from ccms.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(dependencies=[Depends(require_role(Role.ADMIN))])


# --- Maintenance windows (FR-12) ---

@router.get("/maintenance", response_model=list[MaintenanceWindowOut])
def list_maintenance_windows(db: Session = Depends(get_db)) -> list[MaintenanceWindow]:
    return db.query(MaintenanceWindow).order_by(MaintenanceWindow.starts_at.desc()).all()


@router.post("/maintenance", response_model=MaintenanceWindowOut, status_code=status.HTTP_201_CREATED)
def create_maintenance_window(
    payload: MaintenanceWindowCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
) -> MaintenanceWindow:
    window = MaintenanceWindow(**payload.model_dump(), created_by=current_user.id)
    db.add(window)
    db.commit()
    db.refresh(window)
    record_audit(
        db, user=current_user, action="maintenance.create", target_type="maintenance_window", target_id=window.id,
        detail=payload.model_dump(mode="json"), ip=client_ip(request),
    )
    return window


@router.delete("/maintenance/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintenance_window(
    window_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
) -> None:
    window = db.get(MaintenanceWindow, window_id)
    if not window:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Maintenance window not found")
    db.delete(window)
    db.commit()
    record_audit(
        db, user=current_user, action="maintenance.delete", target_type="maintenance_window", target_id=window_id,
        ip=client_ip(request),
    )


# --- Users (FR-13) ---

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
) -> User:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        name=payload.name, email=payload.email, phone=payload.phone,
        password_hash=hash_password(payload.password), role=payload.role, vendor_id=payload.vendor_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit(
        db, user=current_user, action="user.create", target_type="user", target_id=user.id,
        detail={"email": user.email, "role": user.role.value}, ip=client_ip(request),
    )
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    data = payload.model_dump(exclude={"password"}, exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    if payload.password:
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    record_audit(
        db, user=current_user, action="user.update", target_type="user", target_id=user.id,
        detail=data, ip=client_ip(request),
    )
    return user
