# Deployment

## Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker

```bash
docker compose up --build
```

## Recommended hackathon demo flow

1. Launch the dashboard.
2. Run the `morning_peak` scenario.
3. Show baseline vs adaptive metrics.
4. Animate the adaptive timeline on the dashboard.
5. Run the sample video analysis.
6. Explain how the detector feeds lane density into the controller.

## Production upgrade suggestions

- replace motion detector with a trained vehicle detector
- calibrate lane polygons from real CCTV
- add pedestrian phases and protected turns
- connect multiple intersections using corridor coordination
- stream detections over WebSocket or MQTT from edge devices
