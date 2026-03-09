from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api.routes_control import router as control_router
from app.api.routes_health import router as health_router
from app.api.routes_simulation import router as simulation_router
from app.api.routes_vision import router as vision_router
from app.config import STATIC_DIR, settings

INDEX_FILE = Path(STATIC_DIR) / "index.html"
STATIC_ASSETS_AVAILABLE = Path(STATIC_DIR).exists() and INDEX_FILE.exists()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Adaptive traffic signal control demo with simulation and computer vision.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(control_router)
app.include_router(simulation_router)
app.include_router(vision_router)

if STATIC_ASSETS_AVAILABLE:
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> Response:
    if STATIC_ASSETS_AVAILABLE:
        return FileResponse(INDEX_FILE)
    return JSONResponse(
        {
            "name": settings.app_name,
            "status": "ok",
            "docs": "/docs",
        }
    )
