from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import db_session, get_current_user, require_admin
from app.models import Equipment, Hospital, User
from app.schemas import HospitalCreate, HospitalList, HospitalOut, HospitalUpdate
from app.services.query import apply_sort, paginate

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("", response_model=HospitalList)
def list_hospitals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(get_current_user),
) -> HospitalList:
    stmt = select(Hospital)
    if search:
        stmt = stmt.where(Hospital.name.ilike(f"%{search}%"))
    stmt = apply_sort(
        stmt,
        {
            "id": Hospital.id,
            "name": Hospital.name,
            "location_region": Hospital.location_region,
            "capacity": Hospital.capacity,
            "supervisor_id": Hospital.supervisor_id,
        },
        sort_by,
        sort_dir,
    )
    items, total = paginate(stmt, db, page, page_size)
    return HospitalList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{hospital_id}", response_model=HospitalOut)
def get_hospital(
    hospital_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(get_current_user),
) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return hospital


@router.post("", response_model=HospitalOut, status_code=status.HTTP_201_CREATED)
def create_hospital(
    payload: HospitalCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_admin),
) -> Hospital:
    hospital = Hospital(**payload.model_dump())
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


@router.patch("/{hospital_id}", response_model=HospitalOut)
def update_hospital(
    hospital_id: int,
    payload: HospitalUpdate,
    db: Session = Depends(db_session),
    _: User = Depends(require_admin),
) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(hospital, key, value)
    db.commit()
    db.refresh(hospital)
    return hospital


@router.delete("/{hospital_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hospital(
    hospital_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_admin),
) -> None:
    hospital = db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    has_equipment = db.scalar(select(Equipment.id).where(Equipment.facility_id == hospital_id).limit(1))
    has_staff = db.scalar(select(User.id).where(User.facility_id == hospital_id).limit(1))
    if has_equipment or has_staff:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hospital still has equipment or staff assigned",
        )
    db.delete(hospital)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hospital is still referenced") from exc
