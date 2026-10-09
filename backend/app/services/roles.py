from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import Role, RolePermission
from app.permissions import BUILTIN_ROLES, Permission


def permissions_for_role_name(db: Session, role_name: str) -> frozenset[str]:
    rows = db.scalars(
        select(RolePermission.permission)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Role.name == role_name)
    ).all()
    return frozenset(rows)


def sync_builtin_roles(db: Session) -> None:
    """Insert or replace the three built-in roles so a fresh database can authorize."""
    for name, spec in BUILTIN_ROLES.items():
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, description=spec.description)
            db.add(role)
            db.flush()
        else:
            role.description = spec.description
        db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        db.flush()
        for permission in sorted(spec.permissions, key=lambda item: item.value):
            db.add(RolePermission(role_id=role.id, permission=permission.value))
    db.flush()


def replace_role_permissions(db: Session, role: Role, permissions: set[Permission]) -> None:
    db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    db.flush()
    for permission in sorted(permissions, key=lambda item: item.value):
        db.add(RolePermission(role_id=role.id, permission=permission.value))
    db.flush()


def load_role(db: Session, role_id: int) -> Role | None:
    return db.scalar(select(Role).where(Role.id == role_id).options(selectinload(Role.grants)))


def list_roles(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).options(selectinload(Role.grants)).order_by(Role.name)).all())
