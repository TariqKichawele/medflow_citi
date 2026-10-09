from sqlalchemy import Select, asc, desc, false, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.constants import MAX_PAGE_SIZE, ROLE_FIELD_TECHNICIAN, WO_IN_PROGRESS, WO_PENDING
from app.models import Equipment, User, WorkOrder
from app.permissions import Permission, has_permission


class ListQueryError(ValueError):
    pass


def apply_sort(
    stmt: Select,
    columns: dict[str, InstrumentedAttribute],
    sort_by: str | None,
    sort_dir: str | None,
    default: str = "id",
) -> Select:
    if sort_by is not None and sort_by not in columns:
        allowed = ", ".join(sorted(columns))
        raise ListQueryError(f"Unrecognized sort field '{sort_by}'. Allowed values: {allowed}")
    direction = (sort_dir or "asc").lower()
    if direction not in ("asc", "desc"):
        raise ListQueryError("sort_dir must be asc or desc")
    field = sort_by if sort_by in columns else default
    column = columns[field]
    order = desc(column) if direction == "desc" else asc(column)
    if field == default:
        return stmt.order_by(order)
    return stmt.order_by(order, columns[default].asc())


def paginate(stmt: Select, db: Session, page: int, page_size: int) -> tuple[list, int]:
    if page < 1 or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ListQueryError(
            f"page must be at least 1 and page_size must be between 1 and {MAX_PAGE_SIZE}"
        )
    filtered = stmt.order_by(None).limit(None).offset(None)
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return items, total


def equipment_visibility_clause(user: User):
    """Broad ``equipment:read`` sees every device. ``equipment:read_assigned`` sees the caller's facility and assigned orders."""
    if has_permission(user, Permission.EQUIPMENT_READ):
        return None
    if not has_permission(user, Permission.EQUIPMENT_READ_ASSIGNED):
        return false()
    assigned = select(WorkOrder.equipment_id).where(WorkOrder.technician_id == user.id)
    if user.facility_id is None:
        return Equipment.id.in_(assigned)
    return or_(Equipment.facility_id == user.facility_id, Equipment.id.in_(assigned))


def equipment_is_visible(db: Session, user: User, equipment_id: int) -> bool:
    clause = equipment_visibility_clause(user)
    if clause is None:
        return True
    return db.scalar(select(Equipment.id).where(Equipment.id == equipment_id, clause)) is not None


def allowed_technician_status_transition(current: str, new: str) -> bool:
    if current == WO_PENDING and new == WO_IN_PROGRESS:
        return True
    if current == WO_IN_PROGRESS and new in ("completed", "failed"):
        return True
    return False


def require_technician_facility(role: str, facility_id: int | None) -> None:
    if role == ROLE_FIELD_TECHNICIAN and facility_id is None:
        raise ValueError("Field technicians must be assigned to a facility")
