import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ccms.config import settings

logging.basicConfig(level=settings.log_level)

app = FastAPI(title="CCMS API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/v1/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


def _mount_routers() -> None:
    from ccms.api.routers import admin, alerts, auth, devices, integrations, reports, status

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
    app.include_router(status.router, prefix="/api/v1/status", tags=["status"])
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["integrations"])


_mount_routers()

if settings.serve_frontend_dist:
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
