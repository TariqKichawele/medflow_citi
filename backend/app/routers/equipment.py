from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import ListParams, db_session, require_any_permission, require_permission, run_list
from app.models import Equipment, User, WorkOrder
from app.permissions import Permission
from app.schemas import EquipmentCreate, EquipmentOut, EquipmentUpdate, Page
from app.services.query import equipment_is_visible, equipment_visibility_clause

router = APIRouter(prefix="/equipment", tags=["equipment"])

EQUIPMENT_SORT_COLUMNS = {
    "id": Equipment.id,
    "serial_number": Equipment.serial_number,
    "model": Equipment.model,
    "status": Equipment.status,
    "charge_level": Equipment.charge_level,
    "facility_id": Equipment.facility_id,
}


def _visible_equipment_stmt(current: User):
    stmt = select(Equipment)
    clause = equipment_visibility_clause(current)
    if clause is not None:
        stmt = stmt.where(clause)
    return stmt


@router.get("", response_model=Page[EquipmentOut])
def list_equipment(
    params: ListParams = Depends(),
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    facility_id: int | None = None,
    db: Session = Depends(db_session),
    current: User = Depends(
        require_any_permission(Permission.EQUIPMENT_READ, Permission.EQUIPMENT_READ_ASSIGNED)
    ),
) -> Page[EquipmentOut]:
    stmt = _visible_equipment_stmt(current)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Equipment.serial_number.ilike(like), Equipment.model.ilike(like)))
    if status_filter:
        stmt = stmt.where(Equipment.status == status_filter)
    if facility_id is not None:
        stmt = stmt.where(Equipment.facility_id == facility_id)
    items, total = run_list(stmt, db, EQUIPMENT_SORT_COLUMNS, params)
    return Page[EquipmentOut](items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(
        require_any_permission(Permission.EQUIPMENT_READ, Permission.EQUIPMENT_READ_ASSIGNED)
    ),
) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    if not equipment_is_visible(db, current, equipment.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return equipment


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.EQUIPMENT_WRITE)),
) -> Equipment:
    item = Equipment(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Serial number already exists") from exc
    db.refresh(item)
    return item


@router.patch("/{equipment_id}", response_model=EquipmentOut)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.EQUIPMENT_WRITE)),
) -> Equipment:
    item = db.get(Equipment, equipment_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Serial number already exists") from exc
    db.refresh(item)
    return item


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.EQUIPMENT_WRITE)),
) -> None:
    item = db.get(Equipment, equipment_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    has_orders = db.scalar(select(WorkOrder.id).where(WorkOrder.equipment_id == equipment_id).limit(1))
    if has_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Equipment still has work orders",
        )
    db.delete(item)
    db.commit()
