from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_region: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    supervisor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_hospitals_supervisor_id"),
        nullable=True,
    )

    supervisor: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[supervisor_id],
        back_populates="supervised_hospitals",
    )
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="facility")
    staff: Mapped[list["User"]] = relationship(
        "User",
        back_populates="facility",
        foreign_keys="User.facility_id",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("hospitals.id"), nullable=True)
    reports_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    facility: Mapped["Hospital | None"] = relationship(
        "Hospital",
        back_populates="staff",
        foreign_keys=[facility_id],
    )
    supervisor: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[reports_to_id],
        back_populates="direct_reports",
    )
    direct_reports: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys=[reports_to_id],
        back_populates="supervisor",
    )
    supervised_hospitals: Mapped[list["Hospital"]] = relationship(
        "Hospital",
        back_populates="supervisor",
        foreign_keys="Hospital.supervisor_id",
    )
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="technician")
    service_reports: Mapped[list["ServiceReport"]] = relationship(back_populates="uploaded_by")


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (UniqueConstraint("serial_number", name="uq_equipment_serial_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    charge_level: Mapped[int] = mapped_column(Integer, nullable=False)
    facility_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id"), nullable=False, index=True)

    facility: Mapped["Hospital"] = relationship(back_populates="equipment")
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="equipment")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False, index=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    equipment: Mapped["Equipment"] = relationship(back_populates="work_orders")
    technician: Mapped["User"] = relationship(back_populates="work_orders")
    service_reports: Mapped[list["ServiceReport"]] = relationship(back_populates="work_order")


class ServiceReport(Base):
    __tablename__ = "service_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id"), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    work_order: Mapped["WorkOrder"] = relationship(back_populates="service_reports")
    uploaded_by: Mapped["User"] = relationship(back_populates="service_reports")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    grants: Mapped[list["RolePermission"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission", name="uq_role_permissions_role_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(64), nullable=False)

    role: Mapped["Role"] = relationship(back_populates="grants")
