from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.constants import ROLE_FIELD_TECHNICIAN, WO_IN_PROGRESS, WO_PENDING
from app.models import Equipment, WorkOrder


def paginate(stmt: Select, db: Session, page: int, page_size: int) -> tuple[list, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return items, total


def technician_equipment_ids(db: Session, technician_id: int, facility_id: int | None) -> set[int]:
    ids: set[int] = set()
    if facility_id is not None:
        ids.update(
            db.scalars(select(Equipment.id).where(Equipment.facility_id == facility_id)).all()
        )
    assigned = db.scalars(
        select(WorkOrder.equipment_id).where(WorkOrder.technician_id == technician_id)
    ).all()
    ids.update(assigned)
    return ids


def allowed_technician_status_transition(current: str, new: str) -> bool:
    if current == WO_PENDING and new == WO_IN_PROGRESS:
        return True
    if current == WO_IN_PROGRESS and new in ("completed", "failed"):
        return True
    return False


def require_technician_facility(role: str, facility_id: int | None) -> None:
    if role == ROLE_FIELD_TECHNICIAN and facility_id is None:
        raise ValueError("Field technicians must be assigned to a facility")
