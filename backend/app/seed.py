from __future__ import annotations

import os
from urllib.parse import urlparse

from sqlalchemy import delete, update

from app.config import settings
from app.constants import (
    DEMO_PASSWORD,
    EQUIPMENT_AVAILABLE,
    EQUIPMENT_IN_USE,
    EQUIPMENT_MAINTENANCE,
    EQUIPMENT_OFFLINE,
    PRIORITY_CRITICAL,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    ROLE_AUDITOR,
    ROLE_CLINICAL_ADMIN,
    ROLE_FIELD_TECHNICIAN,
    WO_COMPLETED,
    WO_FAILED,
    WO_IN_PROGRESS,
    WO_PENDING,
)
from app.database import SessionLocal
from app.models import Equipment, Hospital, ServiceReport, User, WorkOrder
from app.security import hash_password


def _assert_local_database() -> None:
    parsed = urlparse(settings.database_url.replace("postgresql+psycopg", "postgresql", 1))
    host = (parsed.hostname or "").lower()
    force = os.environ.get("SEED_FORCE", settings.seed_force) == "1"
    if host not in {"localhost", "127.0.0.1"} and not force:
        raise SystemExit(
            f"Refusing to seed database host '{host}'. Set SEED_FORCE=1 to override."
        )


def populate(db) -> None:
    password = hash_password(DEMO_PASSWORD)
    metro = Hospital(name="Halcyon Metro General", location_region="Northeast", capacity=400)
    riverside = Hospital(name="Halcyon Riverside Clinic", location_region="Northeast", capacity=80)
    pacific = Hospital(name="Halcyon Pacific Medical", location_region="West", capacity=350)
    desert = Hospital(name="Halcyon Desert Outpatient", location_region="West", capacity=60)
    db.add_all([metro, riverside, pacific, desert])
    db.flush()

    admin = User(
        email="admin@halcyon.health",
        hashed_password=password,
        full_name="Priya Clinical Admin",
        role=ROLE_CLINICAL_ADMIN,
        is_active=True,
    )
    east = User(
        email="supervisor.east@halcyon.health",
        hashed_password=password,
        full_name="Elena East Supervisor",
        role=ROLE_CLINICAL_ADMIN,
        is_active=True,
    )
    west = User(
        email="supervisor.west@halcyon.health",
        hashed_password=password,
        full_name="Marcus West Supervisor",
        role=ROLE_CLINICAL_ADMIN,
        is_active=True,
    )
    auditor = User(
        email="auditor@halcyon.health",
        hashed_password=password,
        full_name="Owen Auditor",
        role=ROLE_AUDITOR,
        is_active=True,
    )
    db.add_all([admin, east, west, auditor])
    db.flush()

    metro.supervisor_id = east.id
    riverside.supervisor_id = east.id
    pacific.supervisor_id = west.id
    desert.supervisor_id = west.id

    tech_metro = User(
        email="tech.metro@halcyon.health",
        hashed_password=password,
        full_name="Jordan Metro Technician",
        role=ROLE_FIELD_TECHNICIAN,
        facility_id=metro.id,
        reports_to_id=east.id,
    )
    tech_riverside = User(
        email="tech.riverside@halcyon.health",
        hashed_password=password,
        full_name="Sam Riverside Technician",
        role=ROLE_FIELD_TECHNICIAN,
        facility_id=riverside.id,
        reports_to_id=east.id,
    )
    tech_pacific = User(
        email="tech.pacific@halcyon.health",
        hashed_password=password,
        full_name="Riley Pacific Technician",
        role=ROLE_FIELD_TECHNICIAN,
        facility_id=pacific.id,
        reports_to_id=west.id,
    )
    tech_desert = User(
        email="tech.desert@halcyon.health",
        hashed_password=password,
        full_name="Casey Desert Technician",
        role=ROLE_FIELD_TECHNICIAN,
        facility_id=desert.id,
        reports_to_id=west.id,
    )
    db.add_all([tech_metro, tech_riverside, tech_pacific, tech_desert])
    db.flush()

    devices = [
        Equipment(serial_number="INF-001", model="Infusion Pump", status=EQUIPMENT_AVAILABLE, charge_level=15, facility_id=metro.id),
        Equipment(serial_number="INF-002", model="Infusion Pump", status=EQUIPMENT_IN_USE, charge_level=8, facility_id=metro.id),
        Equipment(serial_number="VNT-001", model="Ventilator", status=EQUIPMENT_MAINTENANCE, charge_level=80, facility_id=metro.id),
        Equipment(serial_number="VNT-002", model="Ventilator", status=EQUIPMENT_MAINTENANCE, charge_level=70, facility_id=metro.id),
        Equipment(serial_number="MON-001", model="Patient Monitor", status=EQUIPMENT_AVAILABLE, charge_level=90, facility_id=metro.id),
        Equipment(serial_number="IMG-001", model="Imaging Cart", status=EQUIPMENT_AVAILABLE, charge_level=50, facility_id=metro.id),
        Equipment(serial_number="INF-003", model="Infusion Pump", status=EQUIPMENT_AVAILABLE, charge_level=12, facility_id=riverside.id),
        Equipment(serial_number="VNT-003", model="Ventilator", status=EQUIPMENT_IN_USE, charge_level=45, facility_id=riverside.id),
        Equipment(serial_number="MON-002", model="Patient Monitor", status=EQUIPMENT_MAINTENANCE, charge_level=60, facility_id=riverside.id),
        Equipment(serial_number="MON-003", model="Patient Monitor", status=EQUIPMENT_MAINTENANCE, charge_level=55, facility_id=riverside.id),
        Equipment(serial_number="IMG-002", model="Imaging Cart", status=EQUIPMENT_AVAILABLE, charge_level=88, facility_id=riverside.id),
        Equipment(serial_number="IMG-003", model="Imaging Cart", status=EQUIPMENT_AVAILABLE, charge_level=70, facility_id=riverside.id),
        Equipment(serial_number="OFF-001", model="Infusion Pump", status=EQUIPMENT_OFFLINE, charge_level=5, facility_id=riverside.id),
        Equipment(serial_number="INF-004", model="Infusion Pump", status=EQUIPMENT_IN_USE, charge_level=40, facility_id=pacific.id),
        Equipment(serial_number="VNT-004", model="Ventilator", status=EQUIPMENT_AVAILABLE, charge_level=75, facility_id=pacific.id),
        Equipment(serial_number="MON-004", model="Patient Monitor", status=EQUIPMENT_AVAILABLE, charge_level=82, facility_id=pacific.id),
        Equipment(serial_number="IMG-004", model="Imaging Cart", status=EQUIPMENT_MAINTENANCE, charge_level=30, facility_id=pacific.id),
        Equipment(serial_number="INF-005", model="Infusion Pump", status=EQUIPMENT_AVAILABLE, charge_level=18, facility_id=pacific.id),
        Equipment(serial_number="VNT-005", model="Ventilator", status=EQUIPMENT_IN_USE, charge_level=22, facility_id=pacific.id),
        Equipment(serial_number="INF-006", model="Infusion Pump", status=EQUIPMENT_AVAILABLE, charge_level=95, facility_id=desert.id),
        Equipment(serial_number="VNT-006", model="Ventilator", status=EQUIPMENT_AVAILABLE, charge_level=60, facility_id=desert.id),
        Equipment(serial_number="MON-005", model="Patient Monitor", status=EQUIPMENT_IN_USE, charge_level=10, facility_id=desert.id),
        Equipment(serial_number="IMG-005", model="Imaging Cart", status=EQUIPMENT_AVAILABLE, charge_level=40, facility_id=desert.id),
        Equipment(serial_number="MON-006", model="Patient Monitor", status=EQUIPMENT_AVAILABLE, charge_level=77, facility_id=desert.id),
    ]
    db.add_all(devices)
    db.flush()
    by_serial = {item.serial_number: item for item in devices}

    orders = [
        WorkOrder(
            title="Cross-site infusion pump inspection",
            priority=PRIORITY_CRITICAL,
            status=WO_IN_PROGRESS,
            equipment_id=by_serial["INF-003"].id,
            technician_id=tech_metro.id,
        ),
        WorkOrder(
            title="Metro low-charge pump swap",
            priority=PRIORITY_MEDIUM,
            status=WO_PENDING,
            equipment_id=by_serial["INF-001"].id,
            technician_id=tech_metro.id,
        ),
        WorkOrder(
            title="Riverside ventilator check",
            priority=PRIORITY_MEDIUM,
            status=WO_IN_PROGRESS,
            equipment_id=by_serial["VNT-003"].id,
            technician_id=tech_riverside.id,
        ),
        WorkOrder(
            title="Infusion pump battery replacement",
            priority=PRIORITY_LOW,
            status=WO_COMPLETED,
            equipment_id=by_serial["INF-004"].id,
            technician_id=tech_pacific.id,
        ),
        WorkOrder(
            title="Infusion pump firmware update",
            priority=PRIORITY_LOW,
            status=WO_COMPLETED,
            equipment_id=by_serial["INF-006"].id,
            technician_id=tech_desert.id,
        ),
        WorkOrder(
            title="Infusion pump cassette recall",
            priority=PRIORITY_MEDIUM,
            status=WO_COMPLETED,
            equipment_id=by_serial["INF-002"].id,
            technician_id=tech_metro.id,
        ),
        WorkOrder(
            title="Infusion pump occlusion sensor fail",
            priority=PRIORITY_CRITICAL,
            status=WO_FAILED,
            equipment_id=by_serial["INF-005"].id,
            technician_id=tech_pacific.id,
        ),
        WorkOrder(
            title="Ventilator PM completed",
            priority=PRIORITY_MEDIUM,
            status=WO_COMPLETED,
            equipment_id=by_serial["VNT-004"].id,
            technician_id=tech_pacific.id,
        ),
        WorkOrder(
            title="Ventilator turbine replacement failed",
            priority=PRIORITY_CRITICAL,
            status=WO_FAILED,
            equipment_id=by_serial["VNT-001"].id,
            technician_id=tech_metro.id,
        ),
        WorkOrder(
            title="Ventilator calibration failed",
            priority=PRIORITY_MEDIUM,
            status=WO_FAILED,
            equipment_id=by_serial["VNT-002"].id,
            technician_id=tech_metro.id,
        ),
        WorkOrder(
            title="Ventilator circuit leak unresolved",
            priority=PRIORITY_CRITICAL,
            status=WO_FAILED,
            equipment_id=by_serial["VNT-006"].id,
            technician_id=tech_desert.id,
        ),
        WorkOrder(
            title="Monitor display repair",
            priority=PRIORITY_LOW,
            status=WO_COMPLETED,
            equipment_id=by_serial["MON-001"].id,
            technician_id=tech_metro.id,
        ),
        WorkOrder(
            title="Monitor SpO2 board swap",
            priority=PRIORITY_MEDIUM,
            status=WO_COMPLETED,
            equipment_id=by_serial["MON-004"].id,
            technician_id=tech_pacific.id,
        ),
        WorkOrder(
            title="Monitor NIBP failure",
            priority=PRIORITY_MEDIUM,
            status=WO_FAILED,
            equipment_id=by_serial["MON-005"].id,
            technician_id=tech_desert.id,
        ),
        WorkOrder(
            title="Monitor ECG lead set failed",
            priority=PRIORITY_LOW,
            status=WO_FAILED,
            equipment_id=by_serial["MON-006"].id,
            technician_id=tech_desert.id,
        ),
        WorkOrder(
            title="Imaging cart caster replacement",
            priority=PRIORITY_LOW,
            status=WO_COMPLETED,
            equipment_id=by_serial["IMG-001"].id,
            technician_id=tech_metro.id,
        ),
        WorkOrder(
            title="Imaging cart PACS dongle install",
            priority=PRIORITY_LOW,
            status=WO_COMPLETED,
            equipment_id=by_serial["IMG-002"].id,
            technician_id=tech_riverside.id,
        ),
        WorkOrder(
            title="Imaging cart battery pack swap",
            priority=PRIORITY_MEDIUM,
            status=WO_COMPLETED,
            equipment_id=by_serial["IMG-003"].id,
            technician_id=tech_riverside.id,
        ),
        WorkOrder(
            title="Imaging cart detector cleaning",
            priority=PRIORITY_LOW,
            status=WO_COMPLETED,
            equipment_id=by_serial["IMG-005"].id,
            technician_id=tech_desert.id,
        ),
    ]
    db.add_all(orders)
    db.flush()


def seed() -> None:
    _assert_local_database()
    db = SessionLocal()
    try:
        db.execute(update(Hospital).values(supervisor_id=None))
        db.execute(delete(ServiceReport))
        db.execute(delete(WorkOrder))
        db.execute(delete(Equipment))
        db.execute(delete(User))
        db.execute(delete(Hospital))
        db.commit()
        populate(db)
        db.commit()
        print("Seeded MedFlow demo data.")
        print(f"Shared password: {DEMO_PASSWORD}")
        print("Accounts: admin@halcyon.health, supervisor.east@halcyon.health,")
        print("          supervisor.west@halcyon.health, auditor@halcyon.health,")
        print("          tech.metro@halcyon.health, tech.riverside@halcyon.health,")
        print("          tech.pacific@halcyon.health, tech.desert@halcyon.health")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
