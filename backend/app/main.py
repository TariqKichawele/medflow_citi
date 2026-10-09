from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import db_session, require_permission
from app.health import database_status, detail_status, s3_status
from app.permissions import Permission
from app.routers import analytics, auth, equipment, hospitals, roles, users, work_orders
from app.schemas.analytics import DependencyStatus, HealthDetailResponse, HealthResponse

app = FastAPI(
    title="MedFlow Equipment Command Center",
    version="0.1.0",
    description="Halcyon Health Systems equipment, work order, and analytics API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(hospitals.router, prefix="/api/v1")
app.include_router(equipment.router, prefix="/api/v1")
app.include_router(work_orders.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")

if settings.storage_backend.lower() == "local":
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/health/ready", response_model=HealthResponse)
def health_ready(db: Session = Depends(db_session)) -> HealthResponse | JSONResponse:
    if database_status(db) != "ok":
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return HealthResponse(status="ok")


@app.get("/health/detail", response_model=HealthDetailResponse)
def health_detail(
    db: Session = Depends(db_session),
    _admin=Depends(require_permission(Permission.HEALTH_READ)),
) -> HealthDetailResponse:
    database = database_status(db)
    s3 = s3_status()
    return HealthDetailResponse(
        status=detail_status(database, s3),
        database=DependencyStatus(status=database),
        s3=DependencyStatus(status=s3),
    )


_asgi_handler = Mangum(app, lifespan="off")


def handler(event, context):
    if isinstance(event, dict) and event.get("medflow_action") == "migrate":
        from app.migrate import run_migrate

        return run_migrate(force_seed=bool(event.get("force_seed", False)))
    return _asgi_handler(event, context)
