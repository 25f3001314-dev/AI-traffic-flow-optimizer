from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
DATA_DIR = APP_DIR / "data"
STATIC_DIR = APP_DIR / "static"
SCENARIOS_DIR = DATA_DIR / "scenarios"
DEMO_VIDEO_PATH = DATA_DIR / "demo_video.mp4"
LANE_POLYGONS_PATH = DATA_DIR / "lane_polygons.json"


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Traffic Optimizer Pro")
    debug: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    lane_queue_capacity: int = int(os.getenv("LANE_QUEUE_CAPACITY", "35"))
    idle_fuel_lph: float = float(os.getenv("IDLE_FUEL_LPH", "0.8"))


settings = Settings()
