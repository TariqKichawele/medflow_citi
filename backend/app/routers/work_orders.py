from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ROLE_CLINICAL_ADMIN, ROLE_FIELD_TECHNICIAN
from app.deps import db_session, get_current_user, require_admin
from app.models import ServiceReport, User, WorkOrder
from app.schemas import (
    ServiceReportList,
    ServiceReportOut,
    TechnicianWorkOrderUpdate,
    WorkOrderCreate,
    WorkOrderList,
    WorkOrderOut,
    WorkOrderUpdate,
)
from app.services.query import allowed_technician_status_transition, apply_sort, paginate
from app.services.storage import save_report_file

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


def _visible_work_orders(current: User):
    stmt = select(WorkOrder)
    if current.role == ROLE_FIELD_TECHNICIAN:
        stmt = stmt.where(WorkOrder.technician_id == current.id)
    return stmt


def _can_access_work_order(current: User, order: WorkOrder) -> bool:
    if current.role == ROLE_FIELD_TECHNICIAN:
        return order.technician_id == current.id
    return True


@router.get("", response_model=WorkOrderList)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    technician_id: int | None = None,
    equipment_id: int | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    db: Session = Depends(db_session),
    current: User = Depends(get_current_user),
) -> WorkOrderList:
    stmt = _visible_work_orders(current)
    if search:
        stmt = stmt.where(WorkOrder.title.ilike(f"%{search}%"))
    if status_filter:
        stmt = stmt.where(WorkOrder.status == status_filter)
    if technician_id is not None:
        stmt = stmt.where(WorkOrder.technician_id == technician_id)
    if equipment_id is not None:
        stmt = stmt.where(WorkOrder.equipment_id == equipment_id)
    stmt = apply_sort(
        stmt,
        {
            "id": WorkOrder.id,
            "title": WorkOrder.title,
            "priority": WorkOrder.priority,
            "status": WorkOrder.status,
            "equipment_id": WorkOrder.equipment_id,
            "technician_id": WorkOrder.technician_id,
        },
        sort_by,
        sort_dir,
    )
    items, total = paginate(stmt, db, page, page_size)
    return WorkOrderList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{work_order_id}", response_model=WorkOrderOut)
def get_work_order(
    work_order_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(get_current_user),
) -> WorkOrder:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    if not _can_access_work_order(current, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return order


@router.post("", response_model=WorkOrderOut, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(db_session),
    _: User = Depends(require_admin),
) -> WorkOrder:
    order = WorkOrder(**payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{work_order_id}", response_model=WorkOrderOut)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(get_current_user),
) -> WorkOrder:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    if current.role == ROLE_FIELD_TECHNICIAN:
        if order.technician_id != current.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        updates = payload.model_dump(exclude_unset=True)
        extras = set(updates) - {"status"}
        if extras:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Technicians may only update work order status",
            )
        tech_payload = TechnicianWorkOrderUpdate.model_validate(updates)
        if not allowed_technician_status_transition(order.status, tech_payload.status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot move work order from {order.status} to {tech_payload.status}",
            )
        order.status = tech_payload.status
        db.commit()
        db.refresh(order)
        return order

    if current.role != ROLE_CLINICAL_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(
    work_order_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_admin),
) -> None:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    has_reports = db.scalar(select(ServiceReport.id).where(ServiceReport.work_order_id == work_order_id).limit(1))
    if has_reports:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Work order still has service reports",
        )
    db.delete(order)
    db.commit()


@router.get("/{work_order_id}/reports", response_model=ServiceReportList)
def list_reports(
    work_order_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(db_session),
    current: User = Depends(get_current_user),
) -> ServiceReportList:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    if not _can_access_work_order(current, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    stmt = select(ServiceReport).where(ServiceReport.work_order_id == work_order_id).order_by(ServiceReport.id.asc())
    items, total = paginate(stmt, db, page, page_size)
    return ServiceReportList(items=items, total=total, page=page, page_size=page_size)


@router.post("/{work_order_id}/reports", response_model=ServiceReportOut, status_code=status.HTTP_201_CREATED)
def upload_report(
    work_order_id: int,
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    current: User = Depends(get_current_user),
) -> ServiceReport:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    if current.role == ROLE_FIELD_TECHNICIAN and order.technician_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if current.role not in (ROLE_CLINICAL_ADMIN, ROLE_FIELD_TECHNICIAN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    file_url = save_report_file(file)
    report = ServiceReport(
        work_order_id=order.id,
        file_url=file_url,
        notes=notes,
        uploaded_by_id=current.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
