"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import REPO_DIR, settings
from .db import SessionLocal, init_db
from .domain.ppo import metadata_summary
from .routers import (
    audit,
    auth,
    models_router,
    recommendations,
    scenarios,
    simulations,
)
from .services.seed import seed_default_simulation, seed_users, sync_model_registry
from .services.simulation_service import ServiceError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("railgorithm")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
        sync_model_registry(db)
        seed_default_simulation(db)
    finally:
        db.close()
    if settings.is_default_secret:
        logger.warning(
            "RAILGORITHM_JWT_SECRET is using the development default. "
            "Set a strong secret before any shared deployment."
        )
    yield


app = FastAPI(
    title="RAILGORITHM",
    description=(
        "AI-assisted railway traffic decision support. Recommendations only; "
        "the authorized human controller makes every operational decision."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


for router in (
    auth.router,
    scenarios.router,
    simulations.router,
    recommendations.router,
    audit.router,
    models_router.router,
):
    app.include_router(router, prefix=settings.api_prefix)


@app.get("/api/v1/health")
def health() -> dict:
    summary = metadata_summary()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "human_in_control": True,
        "live_railway_connection": False,
        "data_label": "SYNTHETIC",
        "ppo": {
            "trained": bool(summary.get("trained")),
            "status": summary.get("status", "UNTRAINED_DEVELOPMENT_COMPONENT"),
        },
        "cp_sat_time_limit_s": settings.cp_sat_time_limit_s,
    }


FRONTEND_DIST = REPO_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse(status_code=404, content={"detail": "Frontend build not found"})
