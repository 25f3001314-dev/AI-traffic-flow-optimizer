# Traffic Optimizer Pro

Traffic Optimizer Pro is a hackathon-ready smart traffic signal project for Indian intersections. It includes:

- An adaptive signal controller with fairness, emergency prioritization, and anti-oscillation logic.
- A microscopic queue simulator to compare adaptive control against fixed-time signals.
- A computer-vision pipeline that analyzes intersection video and estimates lane density.
- A zero-build frontend dashboard served directly by FastAPI.
- Tests, Docker support, preset scenarios, and a bundled synthetic demo video.

## Why this project is useful for your hackathon

Most Indian intersections still run on fixed timers, even when one direction is overloaded and another is almost empty. This project dynamically allocates green time to the lanes that need it most, while still preventing starvation on lighter roads.

## Stack

- Backend: FastAPI
- Frontend: HTML, CSS, vanilla JavaScript
- Simulation: Python, NumPy
- Vision: OpenCV with motion-based detection and centroid tracking
- Docs: Markdown

The frontend is intentionally zero-build so the full product can be launched with one backend service during a hackathon.

## Features

### Adaptive controller
- Pressure-based phase scoring
- Dynamic green allocation
- Minimum green / maximum green safety bounds
- Hysteresis to avoid rapid switching
- Emergency vehicle priority bonus
- Starvation protection so low-volume lanes still get served

### Simulation engine
- Fair apples-to-apples comparison using the same arrival schedule for baseline and adaptive runs
- Queueing model with dropped-arrival accounting when lanes overflow
- Wait time, throughput, queue length, idle fuel, and CO2 estimation
- Built-in scenarios: morning peak, balanced, emergency corridor, night mode

### Vision pipeline
- Bundled synthetic intersection demo video
- Motion segmentation using OpenCV background subtraction
- Centroid tracker to stabilize detections
- Lane-wise density estimation from polygon zones
- Upload endpoint for your own overhead intersection clip

### Frontend dashboard
- Scenario picker
- Live animated intersection view
- Baseline vs adaptive comparison charts
- Adaptive decision log
- Demo video analysis panel

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000

FastAPI docs are available at: http://127.0.0.1:8000/docs

## Run tests

```bash
pytest -q
```

## Regenerate the bundled demo video

```bash
python scripts/generate_demo_video.py
```

## Docker

```bash
docker compose up --build
```

## API endpoints

- `GET /api/health`
- `GET /api/simulate/presets`
- `GET /api/simulate/preset/{preset_id}`
- `POST /api/simulate/run?preset_id=morning_peak`
- `POST /api/control/decide`
- `POST /api/vision/analyze-sample`
- `POST /api/vision/analyze-upload`

## Project structure

```text
traffic_optimizer_pro/
├── app/
│   ├── api/
│   ├── core/
│   ├── data/
│   ├── services/
│   ├── static/
│   └── vision/
├── docs/
├── scripts/
└── tests/
```

## Production notes

The bundled CV detector is designed for hackathon demos and stable overhead footage. For production, replace `MotionVehicleDetector` with a trained detector such as YOLO or RT-DETR and calibrate lane polygons from real CCTV views.
