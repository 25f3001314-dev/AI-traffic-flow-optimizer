from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import DEMO_VIDEO_PATH

WIDTH = 960
HEIGHT = 540
FPS = 15
DURATION_S = 24
TOTAL_FRAMES = FPS * DURATION_S


@dataclass(slots=True)
class Vehicle:
    lane: str
    x: float
    y: float
    vx: float
    vy: float
    w: int
    h: int
    color: tuple[int, int, int]

    def update(self) -> None:
        self.x += self.vx
        self.y += self.vy

    def draw(self, frame: np.ndarray) -> None:
        top_left = (int(self.x), int(self.y))
        bottom_right = (int(self.x + self.w), int(self.y + self.h))
        cv2.rectangle(frame, top_left, bottom_right, self.color, -1)
        cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), 1)

    def in_bounds(self) -> bool:
        return -120 <= self.x <= WIDTH + 120 and -120 <= self.y <= HEIGHT + 120


def draw_background(frame: np.ndarray) -> None:
    frame[:] = (12, 18, 28)
    cv2.rectangle(frame, (380, 0), (580, HEIGHT), (56, 63, 74), -1)
    cv2.rectangle(frame, (0, 170), (WIDTH, 370), (56, 63, 74), -1)
    cv2.rectangle(frame, (380, 170), (580, 370), (78, 88, 102), -1)

    for y in range(0, HEIGHT, 26):
        cv2.line(frame, (480, y), (480, min(y + 14, HEIGHT)), (220, 220, 220), 2)
    for x in range(0, WIDTH, 26):
        cv2.line(frame, (x, 270), (min(x + 14, WIDTH), 270), (220, 220, 220), 2)

    cv2.putText(frame, "NORTH", (418, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (234, 241, 255), 2)
    cv2.putText(frame, "SOUTH", (418, 525), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (234, 241, 255), 2)
    cv2.putText(frame, "WEST", (24, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (234, 241, 255), 2)
    cv2.putText(frame, "EAST", (860, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (234, 241, 255), 2)
    cv2.putText(
        frame,
        "Synthetic overhead demo video for computer vision analysis",
        (18, 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (124, 156, 255),
        2,
    )

def spawn_vehicle(lane: str, rng: np.random.Generator) -> Vehicle:
    palette = [
        (124, 156, 255),
        (98, 225, 151),
        (247, 198, 106),
        (255, 122, 144),
        (175, 155, 255),
    ]
    color = palette[int(rng.integers(0, len(palette)))]
    speed = float(rng.uniform(4.5, 6.8))

    if lane == "north":
        return Vehicle(
            lane=lane,
            x=float(rng.integers(420, 452)),
            y=-60.0,
            vx=0.0,
            vy=speed,
            w=24,
            h=40,
            color=color,
        )
    if lane == "south":
        return Vehicle(
            lane=lane,
            x=float(rng.integers(506, 538)),
            y=float(HEIGHT + 20),
            vx=0.0,
            vy=-speed,
            w=24,
            h=40,
            color=color,
        )
    if lane == "east":
        return Vehicle(
            lane=lane,
            x=float(WIDTH + 24),
            y=float(rng.integers(220, 254)),
            vx=-speed,
            vy=0.0,
            w=40,
            h=24,
            color=color,
        )
    return Vehicle(
        lane="west",
        x=-60.0,
        y=float(rng.integers(286, 320)),
        vx=speed,
        vy=0.0,
        w=40,
        h=24,
        color=color,
    )

def main() -> None:
    DEMO_VIDEO_PATH.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(17)
    writer = cv2.VideoWriter(
        str(DEMO_VIDEO_PATH),
        cv2.VideoWriter_fourcc(*"mp4v"),
        FPS,
        (WIDTH, HEIGHT),
    )
    if not writer.isOpened():
        raise RuntimeError("Unable to create demo video file")

    spawn_mod = {
        "north": 5,
        "south": 6,
        "east": 11,
        "west": 10,
    }
    vehicles: list[Vehicle] = []

    for frame_index in range(TOTAL_FRAMES):
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_background(frame)

        for lane, modulus in spawn_mod.items():
            if frame_index % modulus == 0:
                vehicles.append(spawn_vehicle(lane, rng))

        next_vehicles: list[Vehicle] = []
        for vehicle in vehicles:
            vehicle.update()
            if vehicle.in_bounds():
                vehicle.draw(frame)
                next_vehicles.append(vehicle)
        vehicles = next_vehicles

        cv2.putText(
            frame,
            f"Frame {frame_index + 1}/{TOTAL_FRAMES}",
            (18, 64),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (234, 241, 255),
            2,
        )
        writer.write(frame)

    writer.release()
    print(f"Demo video written to {DEMO_VIDEO_PATH}")


if __name__ == "__main__":
    main()
