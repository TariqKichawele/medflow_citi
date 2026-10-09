from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.deps import ListParams, db_session, require_any_permission, require_permission, run_list
from app.models import Equipment, ServiceReport, User, WorkOrder
from app.permissions import Permission, has_permission, missing_permission_detail
from app.schemas import (
    Page,
    ServiceReportOut,
    TechnicianWorkOrderUpdate,
    WorkOrderCreate,
    WorkOrderOut,
    WorkOrderUpdate,
)
from app.services.query import allowed_technician_status_transition
from app.services.storage import save_report_file

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


def _visible_work_orders(current: User):
    stmt = select(WorkOrder)
    if has_permission(current, Permission.WORK_ORDER_READ):
        return stmt
    return stmt.where(WorkOrder.technician_id == current.id)


def _can_access_work_order(current: User, order: WorkOrder) -> bool:
    if has_permission(current, Permission.WORK_ORDER_READ):
        return True
    if has_permission(current, Permission.WORK_ORDER_READ_ASSIGNED):
        return order.technician_id == current.id
    return False


WORK_ORDER_SORT_COLUMNS = {
    "id": WorkOrder.id,
    "title": WorkOrder.title,
    "priority": WorkOrder.priority,
    "status": WorkOrder.status,
    "equipment_id": WorkOrder.equipment_id,
    "technician_id": WorkOrder.technician_id,
}


@router.get("", response_model=Page[WorkOrderOut])
def list_work_orders(
    params: ListParams = Depends(),
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    technician_id: int | None = None,
    equipment_id: int | None = None,
    facility_id: int | None = None,
    db: Session = Depends(db_session),
    current: User = Depends(
        require_any_permission(Permission.WORK_ORDER_READ, Permission.WORK_ORDER_READ_ASSIGNED)
    ),
) -> Page[WorkOrderOut]:
    stmt = _visible_work_orders(current)
    if search:
        like = f"%{search}%"
        matching_equipment = select(Equipment.id).where(
            or_(Equipment.serial_number.ilike(like), Equipment.model.ilike(like))
        )
        stmt = stmt.where(or_(WorkOrder.title.ilike(like), WorkOrder.equipment_id.in_(matching_equipment)))
    if status_filter:
        stmt = stmt.where(WorkOrder.status == status_filter)
    if technician_id is not None:
        stmt = stmt.where(WorkOrder.technician_id == technician_id)
    if equipment_id is not None:
        stmt = stmt.where(WorkOrder.equipment_id == equipment_id)
    if facility_id is not None:
        at_site = select(Equipment.id).where(Equipment.facility_id == facility_id)
        stmt = stmt.where(WorkOrder.equipment_id.in_(at_site))
    items, total = run_list(stmt, db, WORK_ORDER_SORT_COLUMNS, params)
    return Page[WorkOrderOut](items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{work_order_id}", response_model=WorkOrderOut)
def get_work_order(
    work_order_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(
        require_any_permission(Permission.WORK_ORDER_READ, Permission.WORK_ORDER_READ_ASSIGNED)
    ),
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
    _: User = Depends(require_permission(Permission.WORK_ORDER_WRITE)),
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
    current: User = Depends(
        require_any_permission(Permission.WORK_ORDER_WRITE, Permission.WORK_ORDER_STATUS)
    ),
) -> WorkOrder:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    if has_permission(current, Permission.WORK_ORDER_WRITE):
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(order, key, value)
        db.commit()
        db.refresh(order)
        return order

    if not _can_access_work_order(current, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    updates = payload.model_dump(exclude_unset=True)
    extras = set(updates) - {"status"}
    if extras:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=missing_permission_detail(Permission.WORK_ORDER_WRITE),
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


@router.delete("/{work_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(
    work_order_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permission(Permission.WORK_ORDER_WRITE)),
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


@router.get("/{work_order_id}/reports", response_model=Page[ServiceReportOut])
def list_reports(
    work_order_id: int,
    params: ListParams = Depends(),
    db: Session = Depends(db_session),
    current: User = Depends(require_permission(Permission.REPORT_READ)),
) -> Page[ServiceReportOut]:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    if not _can_access_work_order(current, order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    stmt = select(ServiceReport).where(ServiceReport.work_order_id == work_order_id)
    items, total = run_list(
        stmt,
        db,
        {"id": ServiceReport.id, "created_at": ServiceReport.created_at},
        params,
    )
    return Page[ServiceReportOut](items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/{work_order_id}/reports", response_model=ServiceReportOut, status_code=status.HTTP_201_CREATED)
def upload_report(
    work_order_id: int,
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    current: User = Depends(require_permission(Permission.REPORT_UPLOAD)),
) -> ServiceReport:
    order = db.get(WorkOrder, work_order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    if not _can_access_work_order(current, order):
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
