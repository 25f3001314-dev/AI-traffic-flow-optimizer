from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from app.core.schemas import VisionAnalysisResponse, VisionPoint, VisionSummary

from .tracker import CentroidTracker


def load_lane_polygons(path: Path) -> dict[str, np.ndarray]:
    data = json.loads(path.read_text())
    return {lane: np.array(points, dtype=np.int32) for lane, points in data.items()}


class MotionVehicleDetector:
    def __init__(
        self,
        lane_polygons: dict[str, np.ndarray],
        min_area: int = 200,
        max_area: int = 7000,
        queue_capacity: int = 10,
    ) -> None:
        self.lane_polygons = lane_polygons
        self.min_area = min_area
        self.max_area = max_area
        self.queue_capacity = queue_capacity
        self.background = cv2.createBackgroundSubtractorMOG2(
            history=120,
            varThreshold=24,
            detectShadows=False,
        )
        self.tracker = CentroidTracker(max_disappeared=6, max_distance=70.0)
        self.kernel = np.ones((5, 5), dtype=np.uint8)

    def prime(self, frame: np.ndarray) -> None:
        self.background.apply(frame)

    def analyze_frame(self, frame: np.ndarray) -> tuple[dict[str, int], dict[str, float]]:
        foreground_mask = self.background.apply(frame)
        foreground_mask = cv2.morphologyEx(
            foreground_mask,
            cv2.MORPH_OPEN,
            self.kernel,
        )
        foreground_mask = cv2.dilate(foreground_mask, self.kernel, iterations=2)
        contours, _ = cv2.findContours(
            foreground_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        detections: list[tuple[int, int, int, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area or area > self.max_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            detections.append((x, y, w, h))

        tracked = self.tracker.update(detections)
        counts = {lane_id: 0 for lane_id in self.lane_polygons}
        for tracked_object in tracked.values():
            centroid = tracked_object["centroid"]
            for lane_id, polygon in self.lane_polygons.items():
                inside = cv2.pointPolygonTest(
                    polygon,
                    (float(centroid[0]), float(centroid[1])),
                    False,
                )
                if inside >= 0:
                    counts[lane_id] += 1
                    break

        densities = {
            lane_id: round(min(1.0, count / max(self.queue_capacity, 1)), 3)
            for lane_id, count in counts.items()
        }
        return counts, densities


def analyze_video(
    video_path: Path,
    lane_polygons_path: Path,
    sample_every_n_frames: int = 5,
    max_frames: int = 600,
    warmup_frames: int = 20,
) -> VisionAnalysisResponse:
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    lane_polygons = load_lane_polygons(lane_polygons_path)
    detector = MotionVehicleDetector(lane_polygons=lane_polygons)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 15.0)
    points: list[VisionPoint] = []
    frame_index = 0

    while frame_index < max_frames:
        ok, frame = capture.read()
        if not ok:
            break

        if frame_index < warmup_frames:
            detector.prime(frame)
            frame_index += 1
            continue

        if frame_index % sample_every_n_frames != 0:
            detector.prime(frame)
            frame_index += 1
            continue

        counts, densities = detector.analyze_frame(frame)
        points.append(
            VisionPoint(
                frame_index=frame_index,
                timestamp_s=round(frame_index / fps, 2),
                counts=counts,
                densities=densities,
            )
        )
        frame_index += 1

    capture.release()

    lane_ids = list(lane_polygons.keys())
    average_counts = {
        lane_id: round(
            float(np.mean([point.counts.get(lane_id, 0) for point in points])) if points else 0.0,
            2,
        )
        for lane_id in lane_ids
    }
    peak_counts = {
        lane_id: int(max((point.counts.get(lane_id, 0) for point in points), default=0))
        for lane_id in lane_ids
    }
    average_density = {
        lane_id: round(
            float(np.mean([point.densities.get(lane_id, 0.0) for point in points])) if points else 0.0,
            3,
        )
        for lane_id in lane_ids
    }

    return VisionAnalysisResponse(
        video_name=video_path.name,
        fps=round(fps, 2),
        points=points,
        summary=VisionSummary(
            frames_analyzed=len(points),
            average_counts=average_counts,
            peak_counts=peak_counts,
            average_density=average_density,
        ),
    )
