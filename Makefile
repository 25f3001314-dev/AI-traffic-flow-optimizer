run:
	uvicorn app.main:app --reload

test:
	pytest -q

demo-video:
	python scripts/generate_demo_video.py
