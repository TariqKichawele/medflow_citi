from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from app.constants import (
    ACTIVE_EQUIPMENT_STATUSES,
    ACTIVE_WORK_ORDER_STATUSES,
    EQUIPMENT_MAINTENANCE,
    ROLE_FIELD_TECHNICIAN,
    WO_COMPLETED,
    WO_FAILED,
)
from app.models import Equipment, Hospital, User, WorkOrder


def low_charge_devices(db: Session) -> list[dict]:
    rows = db.execute(
        select(Equipment, Hospital.name)
        .join(Hospital, Hospital.id == Equipment.facility_id)
        .where(
            Equipment.status.in_(ACTIVE_EQUIPMENT_STATUSES),
            Equipment.charge_level < 20,
        )
        .order_by(Equipment.charge_level.asc(), Equipment.serial_number.asc())
    ).all()
    return [
        {
            "id": equipment.id,
            "serial_number": equipment.serial_number,
            "model": equipment.model,
            "status": equipment.status,
            "charge_level": equipment.charge_level,
            "facility_id": equipment.facility_id,
            "hospital_name": hospital_name,
        }
        for equipment, hospital_name in rows
    ]


def colocation_discrepancies(db: Session) -> dict:
    rows = db.execute(
        select(
            Equipment.id.label("equipment_id"),
            Equipment.serial_number,
            Equipment.model,
            Equipment.facility_id.label("equipment_facility_id"),
            Hospital.name.label("equipment_hospital"),
            User.id.label("technician_id"),
            User.full_name.label("technician_name"),
            User.facility_id.label("technician_facility_id"),
            WorkOrder.id.label("work_order_id"),
        )
        .join(WorkOrder, WorkOrder.equipment_id == Equipment.id)
        .join(User, User.id == WorkOrder.technician_id)
        .join(Hospital, Hospital.id == Equipment.facility_id)
        .where(
            WorkOrder.status.in_(ACTIVE_WORK_ORDER_STATUSES),
            User.facility_id != Equipment.facility_id,
        )
        .order_by(Equipment.serial_number.asc())
    ).all()
    seen: set[int] = set()
    items: list[dict] = []
    for row in rows:
        if row.equipment_id in seen:
            continue
        seen.add(row.equipment_id)
        items.append(
            {
                "equipment_id": row.equipment_id,
                "serial_number": row.serial_number,
                "model": row.model,
                "equipment_facility_id": row.equipment_facility_id,
                "equipment_hospital": row.equipment_hospital,
                "technician_id": row.technician_id,
                "technician_name": row.technician_name,
                "technician_facility_id": row.technician_facility_id,
                "work_order_id": row.work_order_id,
            }
        )
    return {"count": len(items), "items": items}


def reliability_by_model(db: Session) -> list[dict]:
    completed_count = func.coalesce(
        func.sum(case((WorkOrder.status == WO_COMPLETED, 1), else_=0)),
        0,
    )
    failed_count = func.coalesce(
        func.sum(case((WorkOrder.status == WO_FAILED, 1), else_=0)),
        0,
    )
    rows = db.execute(
        select(
            Equipment.model,
            completed_count.label("completed"),
            failed_count.label("failed"),
        )
        .join(WorkOrder, WorkOrder.equipment_id == Equipment.id)
        .where(WorkOrder.status.in_((WO_COMPLETED, WO_FAILED)))
        .group_by(Equipment.model)
        .order_by(Equipment.model.asc())
    ).all()
    results = []
    for row in rows:
        completed = int(row.completed)
        failed = int(row.failed)
        terminal = completed + failed
        rate = (completed / terminal) if terminal else 0.0
        results.append(
            {
                "model": row.model,
                "completed": completed,
                "failed": failed,
                "completion_rate": round(rate, 4),
            }
        )
    return results


def maintenance_flag_hospitals(db: Session, threshold: float = 0.30) -> list[dict]:
    total = func.count(Equipment.id)
    flagged = func.coalesce(
        func.sum(case((Equipment.status == EQUIPMENT_MAINTENANCE, 1), else_=0)),
        0,
    )
    rows = db.execute(
        select(
            Hospital.id,
            Hospital.name,
            total.label("total_devices"),
            flagged.label("maintenance_devices"),
        )
        .join(Equipment, Equipment.facility_id == Hospital.id)
        .group_by(Hospital.id, Hospital.name)
        .having(flagged * 1.0 / total > threshold)
        .order_by(Hospital.name.asc())
    ).all()
    return [
        {
            "hospital_id": row.id,
            "hospital_name": row.name,
            "total_devices": int(row.total_devices),
            "maintenance_devices": int(row.maintenance_devices),
            "maintenance_ratio": round(int(row.maintenance_devices) / int(row.total_devices), 4),
        }
        for row in rows
    ]


def reporting_lines(db: Session, supervisor_id: int | None = None) -> list[dict]:
    technician = aliased(User)
    supervisor = aliased(User)
    stmt = (
        select(
            technician.reports_to_id.label("supervisor_id"),
            supervisor.full_name.label("supervisor_name"),
            func.count(func.distinct(technician.id)).label("technicians_with_active_orders"),
        )
        .select_from(technician)
        .join(WorkOrder, WorkOrder.technician_id == technician.id)
        .join(supervisor, supervisor.id == technician.reports_to_id)
        .where(
            technician.role == ROLE_FIELD_TECHNICIAN,
            WorkOrder.status.in_(ACTIVE_WORK_ORDER_STATUSES),
            technician.reports_to_id.is_not(None),
        )
        .group_by(technician.reports_to_id, supervisor.full_name)
        .order_by(supervisor.full_name.asc())
    )
    if supervisor_id is not None:
        stmt = stmt.where(technician.reports_to_id == supervisor_id)
    rows = db.execute(stmt).all()
    return [
        {
            "supervisor_id": row.supervisor_id,
            "supervisor_name": row.supervisor_name,
            "technicians_with_active_orders": int(row.technicians_with_active_orders),
        }
        for row in rows
    ]


def analytics_summary(db: Session) -> dict:
    return {
        "low_charge": low_charge_devices(db),
        "colocation_discrepancies": colocation_discrepancies(db),
        "reliability": reliability_by_model(db),
        "maintenance_flags": maintenance_flag_hospitals(db),
        "reporting_lines": reporting_lines(db),
    }
