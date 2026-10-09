from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session, get_current_user
from app.models import User
from app.schemas import LoginRequest, MeOut, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    token = create_access_token(user_id=user.id, email=user.email, role=user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeOut)
def me(current: User = Depends(get_current_user)) -> MeOut:
    granted = getattr(current, "granted_permissions", ())
    return MeOut(
        id=current.id,
        email=current.email,
        full_name=current.full_name,
        role=current.role,
        facility_id=current.facility_id,
        reports_to_id=current.reports_to_id,
        is_active=current.is_active,
        permissions=sorted(granted),
    )
