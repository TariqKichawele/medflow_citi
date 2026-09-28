from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import ROLE_FIELD_TECHNICIAN
from app.deps import db_session, get_current_user, require_admin
from app.models import Equipment, User, WorkOrder
from app.schemas import EquipmentCreate, EquipmentList, EquipmentOut, EquipmentUpdate
from app.services.query import paginate, technician_equipment_ids

router = APIRouter(prefix="/equipment", tags=["equipment"])


def _visible_equipment_stmt(db: Session, current: User):
    stmt = select(Equipment).order_by(Equipment.id.asc())
    if current.role == ROLE_FIELD_TECHNICIAN:
        allowed = technician_equipment_ids(db, current.id, current.facility_id)
        if not allowed:
            stmt = stmt.where(Equipment.id == -1)
        else:
            stmt = stmt.where(Equipment.id.in_(allowed))
    return stmt


@router.get("", response_model=EquipmentList)
def list_equipment(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    facility_id: int | None = None,
    db: Session = Depends(db_session),
    current: User = Depends(get_current_user),
) -> EquipmentList:
    stmt = _visible_equipment_stmt(db, current)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Equipment.serial_number.ilike(like), Equipment.model.ilike(like)))
    if status_filter:
        stmt = stmt.where(Equipment.status == status_filter)
    if facility_id is not None:
        stmt = stmt.where(Equipment.facility_id == facility_id)
    items, total = paginate(stmt, db, page, page_size)
    return EquipmentList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(get_current_user),
) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    if current.role == ROLE_FIELD_TECHNICIAN:
        allowed = technician_equipment_ids(db, current.id, current.facility_id)
        if equipment.id not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return equipment


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_admin),
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
    _: User = Depends(require_admin),
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
    _: User = Depends(require_admin),
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
