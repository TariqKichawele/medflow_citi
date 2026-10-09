from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import db_session, require_permission
from app.models import User
from app.permissions import Permission
from app.schemas.analytics import (
    AnalyticsSummary,
    ColocationResponse,
    LowChargeResponse,
    MaintenanceFlagResponse,
    ReliabilityResponse,
    ReportingLineResponse,
)
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/low-charge", response_model=LowChargeResponse)
def low_charge(_: User = Depends(require_permission(Permission.ANALYTICS_READ)), db: Session = Depends(db_session)) -> LowChargeResponse:
    items = analytics_service.low_charge_devices(db)
    return LowChargeResponse(count=len(items), items=items)


@router.get("/colocation-discrepancies", response_model=ColocationResponse)
def colocation(_: User = Depends(require_permission(Permission.ANALYTICS_READ)), db: Session = Depends(db_session)) -> ColocationResponse:
    return ColocationResponse.model_validate(analytics_service.colocation_discrepancies(db))


@router.get("/reliability", response_model=ReliabilityResponse)
def reliability(_: User = Depends(require_permission(Permission.ANALYTICS_READ)), db: Session = Depends(db_session)) -> ReliabilityResponse:
    return ReliabilityResponse(items=analytics_service.reliability_by_model(db))


@router.get("/maintenance-flags", response_model=MaintenanceFlagResponse)
def maintenance_flags(
    _: User = Depends(require_permission(Permission.ANALYTICS_READ)), db: Session = Depends(db_session)
) -> MaintenanceFlagResponse:
    return MaintenanceFlagResponse(items=analytics_service.maintenance_flag_hospitals(db))


@router.get("/reporting-lines", response_model=ReportingLineResponse)
def reporting_lines(
    supervisor_id: int | None = Query(default=None),
    _: User = Depends(require_permission(Permission.ANALYTICS_READ)),
    db: Session = Depends(db_session),
) -> ReportingLineResponse:
    return ReportingLineResponse(items=analytics_service.reporting_lines(db, supervisor_id=supervisor_id))


@router.get("/summary", response_model=AnalyticsSummary)
def summary(_: User = Depends(require_permission(Permission.ANALYTICS_READ)), db: Session = Depends(db_session)) -> AnalyticsSummary:
    return AnalyticsSummary.model_validate(analytics_service.analytics_summary(db))
