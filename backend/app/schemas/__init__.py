from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.constants import (
    EQUIPMENT_STATUSES,
    PRIORITIES,
    ROLES,
    WORK_ORDER_STATUSES,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: str
    password: str = Field(min_length=8, max_length=128)
    facility_id: int | None = None
    reports_to_id: int | None = None
    is_active: bool = True

    @field_validator("role")
    @classmethod
    def role_ok(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError(f"must be one of {ROLES}")
        return value


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = None
    facility_id: int | None = None
    reports_to_id: int | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("role")
    @classmethod
    def role_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in ROLES:
            raise ValueError(f"must be one of {ROLES}")
        return value


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    facility_id: int | None
    reports_to_id: int | None
    is_active: bool


class UserList(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class HospitalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location_region: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1)
    supervisor_id: int | None = None


class HospitalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_region: str | None = Field(default=None, min_length=1, max_length=100)
    capacity: int | None = Field(default=None, ge=1)
    supervisor_id: int | None = None


class HospitalOut(ORMModel):
    id: int
    name: str
    location_region: str
    capacity: int
    supervisor_id: int | None


class HospitalList(BaseModel):
    items: list[HospitalOut]
    total: int
    page: int
    page_size: int


class EquipmentCreate(BaseModel):
    serial_number: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=150)
    status: str
    charge_level: int = Field(ge=0, le=100)
    facility_id: int

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str) -> str:
        if value not in EQUIPMENT_STATUSES:
            raise ValueError(f"must be one of {EQUIPMENT_STATUSES}")
        return value


class EquipmentUpdate(BaseModel):
    serial_number: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=150)
    status: str | None = None
    charge_level: int | None = Field(default=None, ge=0, le=100)
    facility_id: int | None = None

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in EQUIPMENT_STATUSES:
            raise ValueError(f"must be one of {EQUIPMENT_STATUSES}")
        return value


class EquipmentOut(ORMModel):
    id: int
    serial_number: str
    model: str
    status: str
    charge_level: int
    facility_id: int


class EquipmentList(BaseModel):
    items: list[EquipmentOut]
    total: int
    page: int
    page_size: int


class WorkOrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    priority: str
    status: str = "pending"
    equipment_id: int
    technician_id: int

    @field_validator("priority")
    @classmethod
    def priority_ok(cls, value: str) -> str:
        if value not in PRIORITIES:
            raise ValueError(f"must be one of {PRIORITIES}")
        return value

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str) -> str:
        if value not in WORK_ORDER_STATUSES:
            raise ValueError(f"must be one of {WORK_ORDER_STATUSES}")
        return value


class WorkOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    priority: str | None = None
    status: str | None = None
    equipment_id: int | None = None
    technician_id: int | None = None

    @field_validator("priority")
    @classmethod
    def priority_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in PRIORITIES:
            raise ValueError(f"must be one of {PRIORITIES}")
        return value

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in WORK_ORDER_STATUSES:
            raise ValueError(f"must be one of {WORK_ORDER_STATUSES}")
        return value


class TechnicianWorkOrderUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str) -> str:
        if value not in WORK_ORDER_STATUSES:
            raise ValueError(f"must be one of {WORK_ORDER_STATUSES}")
        return value


class WorkOrderOut(ORMModel):
    id: int
    title: str
    priority: str
    status: str
    equipment_id: int
    technician_id: int


class WorkOrderList(BaseModel):
    items: list[WorkOrderOut]
    total: int
    page: int
    page_size: int


class ServiceReportOut(ORMModel):
    id: int
    work_order_id: int
    file_url: str
    notes: str | None
    created_at: datetime
    uploaded_by_id: int


class ServiceReportList(BaseModel):
    items: list[ServiceReportOut]
    total: int
    page: int
    page_size: int
