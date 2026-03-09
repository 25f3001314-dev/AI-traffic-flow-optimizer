from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PhaseDefinition(BaseModel):
    name: str
    green_lanes: list[str]
    min_green_s: int = 12
    max_green_s: int = 40
    amber_s: int = 3
    all_red_s: int = 1


def default_phases() -> list[PhaseDefinition]:
    return [
        PhaseDefinition(name="north_south", green_lanes=["north", "south"]),
        PhaseDefinition(name="east_west", green_lanes=["east", "west"]),
    ]


class LaneState(BaseModel):
    id: str
    queue_length: int = 0
    density: float = 0.0
    average_speed_kph: float = 0.0
    waiting_seconds: float = 0.0
    emergency_vehicle: bool = False


class JunctionState(BaseModel):
    lanes: list[LaneState]
    phases: list[PhaseDefinition] = Field(default_factory=default_phases)
    current_phase: str | None = None
    time_in_current_phase_s: int = 0


class ControllerWeights(BaseModel):
    density_weight: float = 40.0
    queue_weight: float = 7.5
    wait_weight: float = 0.18
    speed_penalty_weight: float = 0.35
    emergency_bonus: float = 120.0
    starvation_weight: float = 0.65
    continuity_bonus: float = 18.0
    switch_hysteresis: float = 0.92
    queue_capacity: int = 35


class DecisionRequest(BaseModel):
    junction_state: JunctionState
    history: dict[str, float] = Field(default_factory=dict)
    weights: ControllerWeights = Field(default_factory=ControllerWeights)


class DecisionResponse(BaseModel):
    selected_phase: str
    green_duration_s: int
    scores: dict[str, float]
    phase_breakdown: dict[str, dict[str, float]]
    congestion_index: float
    reason: str
    history: dict[str, float]


class DemandSegment(BaseModel):
    start_s: int
    end_s: int
    arrival_rate_vph: float
    emergency_probability: float = 0.0


class LaneDemandProfile(BaseModel):
    lane_id: str
    segments: list[DemandSegment]


class SimulationConfig(BaseModel):
    duration_s: int = 300
    random_seed: int = 42
    sample_step_s: int = 5
    saturation_flow_vps: float = 0.65
    queue_capacity: int = 35
    baseline_fixed_green_s: int = 24
    idle_fuel_lph: float = 0.8


class SimulationRequest(BaseModel):
    name: str
    description: str
    profiles: list[LaneDemandProfile]
    config: SimulationConfig = Field(default_factory=SimulationConfig)
    phases: list[PhaseDefinition] = Field(default_factory=default_phases)


class DecisionEvent(BaseModel):
    t: int
    selected_phase: str
    green_duration_s: int
    reason: str
    scores: dict[str, float]


class TimelinePoint(BaseModel):
    t: int
    phase: str | None
    stage: Literal["green", "transition", "idle"]
    queue_lengths: dict[str, int]
    densities: dict[str, float]
    throughput: int
    avg_wait_s: float


class SimulationMetrics(BaseModel):
    total_arrivals: int
    dropped_arrivals: int
    throughput: int
    average_wait_s: float
    p95_wait_s: float
    max_total_queue: int
    mean_total_queue: float
    total_idle_vehicle_seconds: float
    estimated_idle_fuel_l: float
    estimated_co2_kg: float


class SimulationRun(BaseModel):
    controller_name: str
    metrics: SimulationMetrics
    timeline: list[TimelinePoint]
    decisions: list[DecisionEvent]


class ImprovementSummary(BaseModel):
    wait_time_reduction_pct: float
    throughput_improvement_pct: float
    max_queue_reduction_pct: float
    co2_reduction_pct: float


class SimulationComparison(BaseModel):
    scenario_name: str
    scenario_description: str
    baseline: SimulationRun
    adaptive: SimulationRun
    improvements: ImprovementSummary


class PresetSummary(BaseModel):
    preset_id: str
    name: str
    description: str


class VisionPoint(BaseModel):
    frame_index: int
    timestamp_s: float
    counts: dict[str, int]
    densities: dict[str, float]


class VisionSummary(BaseModel):
    frames_analyzed: int
    average_counts: dict[str, float]
    peak_counts: dict[str, int]
    average_density: dict[str, float]


class VisionAnalysisResponse(BaseModel):
    video_name: str
    fps: float
    points: list[VisionPoint]
    summary: VisionSummary
