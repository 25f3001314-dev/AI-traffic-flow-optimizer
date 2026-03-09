from __future__ import annotations

import numpy as np


class CentroidTracker:
    def __init__(self, max_disappeared: int = 8, max_distance: float = 80.0) -> None:
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.next_object_id = 0
        self.objects: dict[int, dict[str, tuple[int, int] | tuple[int, int, int, int]]] = {}
        self.disappeared: dict[int, int] = {}

    def register(self, bbox: tuple[int, int, int, int]) -> None:
        x, y, w, h = bbox
        centroid = (int(x + w / 2), int(y + h / 2))
        self.objects[self.next_object_id] = {"centroid": centroid, "bbox": bbox}
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1

    def deregister(self, object_id: int) -> None:
        self.objects.pop(object_id, None)
        self.disappeared.pop(object_id, None)

    def update(
        self,
        detections: list[tuple[int, int, int, int]],
    ) -> dict[int, dict[str, tuple[int, int] | tuple[int, int, int, int]]]:
        if not detections:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.objects

        input_centroids = np.array(
            [[x + w / 2.0, y + h / 2.0] for x, y, w, h in detections],
            dtype=float,
        )

        if not self.objects:
            for bbox in detections:
                self.register(bbox)
            return self.objects

        object_ids = list(self.objects.keys())
        object_centroids = np.array(
            [self.objects[object_id]["centroid"] for object_id in object_ids],
            dtype=float,
        )
        distances = np.linalg.norm(
            object_centroids[:, None, :] - input_centroids[None, :, :],
            axis=2,
        )

        rows = distances.min(axis=1).argsort()
        cols = distances.argmin(axis=1)[rows]
        used_rows: set[int] = set()
        used_cols: set[int] = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue
            if distances[row, col] > self.max_distance:
                continue
            object_id = object_ids[row]
            bbox = detections[col]
            x, y, w, h = bbox
            centroid = (int(x + w / 2), int(y + h / 2))
            self.objects[object_id] = {"centroid": centroid, "bbox": bbox}
            self.disappeared[object_id] = 0
            used_rows.add(row)
            used_cols.add(col)

        unused_rows = set(range(distances.shape[0])) - used_rows
        unused_cols = set(range(distances.shape[1])) - used_cols

        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self.deregister(object_id)

        for col in unused_cols:
            self.register(detections[col])

        return self.objects
