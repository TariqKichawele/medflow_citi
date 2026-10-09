from collections.abc import Callable, Generator

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import Select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.constants import MAX_PAGE_SIZE
from app.database import get_db
from app.models import User
from app.permissions import Permission, has_permission, missing_permission_detail
from app.security import decode_access_token
from app.services.query import ListQueryError, apply_sort, paginate
from app.services.roles import permissions_for_role_name

bearer_scheme = HTTPBearer(auto_error=False)


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


class ListParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
        sort_by: str | None = Query(default=None),
        sort_dir: str | None = Query(default=None),
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.sort_by = sort_by
        self.sort_dir = sort_dir


def run_list(
    stmt: Select,
    db: Session,
    columns: dict[str, InstrumentedAttribute],
    params: ListParams,
    default: str = "id",
) -> tuple[list, int]:
    try:
        ordered = apply_sort(stmt, columns, params.sort_by, params.sort_dir, default)
        return paginate(ordered, db, params.page, params.page_size)
    except ListQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or missing user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.granted_permissions = permissions_for_role_name(db, user.role)
    return user


def require_permission(permission: Permission) -> Callable[[User], User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=missing_permission_detail(permission),
            )
        return user

    checker.permission_dependency = True  # type: ignore[attr-defined]
    return checker


def require_any_permission(*permissions: Permission) -> Callable[[User], User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if not any(has_permission(user, permission) for permission in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=missing_permission_detail(*permissions),
            )
        return user

    checker.permission_dependency = True  # type: ignore[attr-defined]
    return checker


def require_self_or_permission(permission: Permission) -> Callable[..., User]:
    def checker(user_id: int, user: User = Depends(get_current_user)) -> User:
        if user.id != user_id and not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=missing_permission_detail(permission),
            )
        return user

    checker.permission_dependency = True  # type: ignore[attr-defined]
    return checker
