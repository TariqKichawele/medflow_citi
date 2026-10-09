from datetime import datetime

from pydantic import BaseModel


class LowChargeItem(BaseModel):
    id: int
    serial_number: str
    model: str
    status: str
    charge_level: int
    facility_id: int
    hospital_name: str


class LowChargeResponse(BaseModel):
    count: int
    items: list[LowChargeItem]


class ColocationItem(BaseModel):
    equipment_id: int
    serial_number: str
    model: str
    equipment_facility_id: int
    equipment_hospital: str
    technician_id: int
    technician_name: str
    technician_facility_id: int | None
    work_order_id: int


class ColocationResponse(BaseModel):
    count: int
    items: list[ColocationItem]


class ReliabilityItem(BaseModel):
    model: str
    completed: int
    failed: int
    completion_rate: float


class ReliabilityResponse(BaseModel):
    items: list[ReliabilityItem]


class MaintenanceFlagItem(BaseModel):
    hospital_id: int
    hospital_name: str
    total_devices: int
    maintenance_devices: int
    maintenance_ratio: float


class MaintenanceFlagResponse(BaseModel):
    items: list[MaintenanceFlagItem]


class ReportingLineItem(BaseModel):
    supervisor_id: int
    supervisor_name: str
    technicians_with_active_orders: int


class ReportingLineResponse(BaseModel):
    items: list[ReportingLineItem]


class AnalyticsSummary(BaseModel):
    low_charge: list[LowChargeItem]
    colocation_discrepancies: ColocationResponse
    reliability: list[ReliabilityItem]
    maintenance_flags: list[MaintenanceFlagItem]
    reporting_lines: list[ReportingLineItem]


class HealthResponse(BaseModel):
    status: str


class DependencyStatus(BaseModel):
    status: str


class HealthDetailResponse(BaseModel):
    status: str
    database: DependencyStatus
    s3: DependencyStatus
