from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query

from app.core.schemas import PresetSummary, SimulationComparison, SimulationRequest
from app.core.simulator import TrafficSimulator
from app.services.preset_loader import get_preset, list_preset_summaries

router = APIRouter(prefix="/api/simulate", tags=["simulation"])


@router.get("/presets", response_model=list[PresetSummary])
def presets() -> list[PresetSummary]:
    return list_preset_summaries()


@router.get("/preset/{preset_id}", response_model=SimulationRequest)
def preset_detail(preset_id: str) -> SimulationRequest:
    preset = get_preset(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.post("/run", response_model=SimulationComparison)
def run_simulation(
    preset_id: str | None = Query(default=None),
    request: SimulationRequest | None = Body(default=None),
) -> SimulationComparison:
    if preset_id:
        preset = get_preset(preset_id)
        if preset is None:
            raise HTTPException(status_code=404, detail="Preset not found")
        request = preset
    elif request is None:
        request = get_preset("morning_peak")

    if request is None:
        raise HTTPException(status_code=400, detail="No scenario payload could be resolved")

    simulator = TrafficSimulator(request=request)
    return simulator.run_comparison()
