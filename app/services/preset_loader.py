from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.config import SCENARIOS_DIR
from app.core.schemas import PresetSummary, SimulationRequest


@lru_cache(maxsize=1)
def load_presets() -> dict[str, SimulationRequest]:
    presets: dict[str, SimulationRequest] = {}
    for path in sorted(Path(SCENARIOS_DIR).glob("*.json")):
        data = json.loads(path.read_text())
        presets[path.stem] = SimulationRequest.model_validate(data)
    return presets


def get_preset(preset_id: str) -> SimulationRequest | None:
    return load_presets().get(preset_id)


def list_preset_summaries() -> list[PresetSummary]:
    presets = load_presets()
    return [
        PresetSummary(
            preset_id=preset_id,
            name=request.name,
            description=request.description,
        )
        for preset_id, request in presets.items()
    ]
