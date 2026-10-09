from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import ListParams, db_session, require_permission, run_list
from app.permissions import Permission
from app.models import Equipment, Hospital, User
from app.schemas import HospitalCreate, HospitalOut, HospitalUpdate, Page

router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@router.get("", response_model=Page[HospitalOut])
def list_hospitals(
    params: ListParams = Depends(),
    search: str | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.HOSPITAL_READ)),
) -> Page[HospitalOut]:
    stmt = select(Hospital)
    if search:
        stmt = stmt.where(Hospital.name.ilike(f"%{search}%"))
    items, total = run_list(
        stmt,
        db,
        {
            "id": Hospital.id,
            "name": Hospital.name,
            "location_region": Hospital.location_region,
            "capacity": Hospital.capacity,
            "supervisor_id": Hospital.supervisor_id,
        },
        params,
    )
    return Page[HospitalOut](items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{hospital_id}", response_model=HospitalOut)
def get_hospital(
    hospital_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.HOSPITAL_READ)),
) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return hospital


@router.post("", response_model=HospitalOut, status_code=status.HTTP_201_CREATED)
def create_hospital(
    payload: HospitalCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.HOSPITAL_WRITE)),
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
    _: User = Depends(require_permission(Permission.HOSPITAL_WRITE)),
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
    _: User = Depends(require_permission(Permission.HOSPITAL_WRITE)),
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
