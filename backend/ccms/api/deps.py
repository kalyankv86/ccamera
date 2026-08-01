from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ccms.auth.security import decode_access_token
from ccms.db import get_db
from ccms.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    if not token:
        raise unauthorized
    payload = decode_access_token(token)
    if not payload:
        raise unauthorized
    user = db.get(User, payload.get("uid"))
    if not user or not user.active:
        raise unauthorized
    return user


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
