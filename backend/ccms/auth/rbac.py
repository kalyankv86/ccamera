from fastapi import Depends, HTTPException, status

from ccms.models.enums import Role
from ccms.models.user import User


def require_role(*roles: Role):
    """FastAPI dependency factory: 403s unless current_user.role is one of `roles`."""
    from ccms.api.deps import get_current_user  # local import: avoids deps.py <-> rbac.py cycle

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user

    return _check
