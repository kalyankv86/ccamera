from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ccms.api.deps import client_ip, get_current_user, get_db
from ccms.audit.logger import record_audit
from ccms.auth.security import (
    LOCKOUT_MINUTES,
    LOCKOUT_THRESHOLD,
    create_access_token,
    verify_password,
)
from ccms.models.user import User
from ccms.schemas.auth import CurrentUser, LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user or not user.active:
        raise invalid

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_423_LOCKED, detail="Account temporarily locked; try again later")

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= LOCKOUT_THRESHOLD:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        db.commit()
        raise invalid

    user.failed_login_count = 0
    user.locked_until = None
    db.commit()

    record_audit(db, user=user, action="login", target_type="user", target_id=user.id, ip=client_ip(request))
    token = create_access_token(subject=user.email, role=user.role.value, user_id=user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUser)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
