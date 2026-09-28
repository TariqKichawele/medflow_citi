from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import analytics, auth, equipment, hospitals, users, work_orders
from app.schemas.analytics import HealthResponse

app = FastAPI(
    title="MedFlow Clinical Equipment Command Center",
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

upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
