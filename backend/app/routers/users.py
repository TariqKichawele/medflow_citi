from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import (
    ListParams,
    db_session,
    require_permission,
    require_self_or_permission,
    run_list,
)
from app.models import Role, User
from app.permissions import Permission
from app.schemas import Page, UserCreate, UserOut, UserUpdate
from app.security import hash_password
from app.services.query import require_technician_facility

router = APIRouter(prefix="/users", tags=["users"])


def _require_known_role(db: Session, role_name: str) -> None:
    found = db.scalar(select(Role.id).where(Role.name == role_name))
    if found is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown role '{role_name}'")


@router.get("", response_model=Page[UserOut])
def list_users(
    params: ListParams = Depends(),
    search: str | None = None,
    role: str | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.USER_READ)),
) -> Page[UserOut]:
    stmt = select(User)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
    if role:
        stmt = stmt.where(User.role == role)
    items, total = run_list(
        stmt,
        db,
        {
            "id": User.id,
            "email": User.email,
            "full_name": User.full_name,
            "role": User.role,
            "facility_id": User.facility_id,
            "reports_to_id": User.reports_to_id,
            "is_active": User.is_active,
        },
        params,
    )
    return Page[UserOut](items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_self_or_permission(Permission.USER_READ)),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.USER_MANAGE)),
) -> User:
    _require_known_role(db, payload.role)
    try:
        require_technician_facility(payload.role, payload.facility_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    user = User(
        email=str(payload.email).lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        facility_id=payload.facility_id,
        reports_to_id=payload.reports_to_id,
        is_active=payload.is_active,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.USER_MANAGE)),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).lower()
    for key, value in data.items():
        setattr(user, key, value)
    if password:
        user.hashed_password = hash_password(password)
    _require_known_role(db, user.role)
    try:
        require_technician_facility(user.role, user.facility_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permission(Permission.USER_MANAGE)),
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot deactivate yourself")
    user.is_active = False
    db.commit()
