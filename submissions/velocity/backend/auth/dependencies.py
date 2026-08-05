"""FastAPI dependencies for authentication and role-based access control."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth.security import decode_access_token
from database import get_db
from models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_exception

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(*allowed_roles: UserRole):
    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _dependency


require_admin = require_roles(UserRole.ADMIN)
require_analyst_or_admin = require_roles(UserRole.ADMIN, UserRole.SECURITY_ANALYST)
