"""
Authentication endpoints: register, login, current-user profile.

Security note (Milestone 6 hardening): POST /register is a PUBLIC,
unauthenticated endpoint - it must never let the caller choose their own
role. Earlier milestones accepted `payload.role` directly from the client,
which let anyone self-register as "admin" and immediately receive an
admin JWT. Public self-registration is now hardcoded to UserRole.EMPLOYEE;
provisioning an admin or security_analyst account is an intentionally
out-of-band operation (seed.py, or a future admin-only "create user"
endpoint), never something a public POST body can request.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from auth.dependencies import get_current_user
from auth.security import create_access_token, hash_password, verify_password
from database import get_db
from models.user import User, UserRole
from schemas.auth import Token, UserCreate, UserLogin, UserOut
from services.employee_service import get_live_extension_status

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Never trust a client-supplied role on a public, unauthenticated
    # endpoint - self-registration always creates a plain employee account.
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        department=payload.department,
        role=UserRole.EMPLOYEE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role.value)
    user_out = UserOut.model_validate(user).model_copy(
        update={"extension_status": get_live_extension_status(db, user)}
    )
    return Token(access_token=token, user=user_out)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    token = create_access_token(subject=user.id, role=user.role.value)
    user_out = UserOut.model_validate(user).model_copy(
        update={"extension_status": get_live_extension_status(db, user)}
    )
    return Token(access_token=token, user=user_out)


@router.get("/me", response_model=UserOut)
def read_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UserOut.model_validate(current_user).model_copy(
        update={"extension_status": get_live_extension_status(db, current_user)}
    )
