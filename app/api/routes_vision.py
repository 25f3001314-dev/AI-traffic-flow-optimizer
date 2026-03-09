from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import DEMO_VIDEO_PATH, LANE_POLYGONS_PATH
from app.core.schemas import VisionAnalysisResponse

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/analyze-sample", response_model=VisionAnalysisResponse)
def analyze_sample() -> VisionAnalysisResponse:
    try:
        from app.vision.detector import analyze_video
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Vision dependencies are unavailable in this deployment environment",
        ) from exc

    if not DEMO_VIDEO_PATH.exists():
        raise HTTPException(status_code=404, detail="Bundled demo video is missing")
    return analyze_video(
        video_path=DEMO_VIDEO_PATH,
        lane_polygons_path=LANE_POLYGONS_PATH,
    )


@router.post("/analyze-upload", response_model=VisionAnalysisResponse)
async def analyze_upload(file: UploadFile = File(...)) -> VisionAnalysisResponse:
    try:
        from app.vision.detector import analyze_video
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Vision dependencies are unavailable in this deployment environment",
        ) from exc

    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = Path(temp_file.name)

    try:
        return analyze_video(
            video_path=temp_path,
            lane_polygons_path=LANE_POLYGONS_PATH,
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)
