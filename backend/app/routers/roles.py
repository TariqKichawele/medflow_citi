from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import db_session, require_permission
from app.models import Role, RolePermission, User
from app.permissions import Permission
from app.schemas import PermissionCatalog, RoleCreate, RoleOut, RoleUpdate
from app.services.roles import list_roles, load_role, replace_role_permissions

router = APIRouter(prefix="/roles", tags=["roles"])


def _role_out(db: Session, role: Role) -> RoleOut:
    names = db.scalars(
        select(RolePermission.permission)
        .where(RolePermission.role_id == role.id)
        .order_by(RolePermission.permission)
    ).all()
    return RoleOut(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=list(names),
    )


@router.get("/permissions", response_model=PermissionCatalog)
def list_permissions(_: User = Depends(require_permission(Permission.ROLE_READ))) -> PermissionCatalog:
    return PermissionCatalog(permissions=sorted(permission.value for permission in Permission))


@router.get("", response_model=list[RoleOut])
def get_roles(
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.ROLE_READ)),
) -> list[RoleOut]:
    return [_role_out(db, role) for role in list_roles(db)]


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.ROLE_MANAGE)),
) -> RoleOut:
    role = Role(
        name=payload.name,
        description=payload.description,
        grants=[RolePermission(permission=permission.value) for permission in dict.fromkeys(payload.permissions)],
    )
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists") from exc
    stored = load_role(db, role.id)
    if stored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return _role_out(db, stored)


@router.patch("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.ROLE_MANAGE)),
) -> RoleOut:
    role = load_role(db, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if payload.description is not None:
        role.description = payload.description
    if payload.permissions is not None:
        replace_role_permissions(db, role, set(payload.permissions))
    db.commit()
    stored = load_role(db, role.id)
    if stored is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return _role_out(db, stored)
