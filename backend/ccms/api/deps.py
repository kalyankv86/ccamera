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


def get_current_user_flexible(
    request: Request, token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Same as get_current_user, but also accepts ?token=... - for the handful
    of endpoints a browser loads via a plain tag (e.g. <img src=snapshot>)
    rather than fetch(), which can't attach an Authorization header."""
    query_token = request.query_params.get("token")
    return get_current_user(token or query_token, db)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
