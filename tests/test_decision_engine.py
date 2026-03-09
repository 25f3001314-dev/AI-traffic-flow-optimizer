from app.core.decision_engine import DecisionEngine
from app.core.schemas import JunctionState, LaneState, default_phases


def build_lane(lane_id: str, queue: int, density: float, wait: float, speed: float, emergency: bool = False) -> LaneState:
    return LaneState(
        id=lane_id,
        queue_length=queue,
        density=density,
        waiting_seconds=wait,
        average_speed_kph=speed,
        emergency_vehicle=emergency,
    )


def test_engine_prioritizes_heavy_north_south_flow() -> None:
    state = JunctionState(
        lanes=[
            build_lane("north", 22, 0.82, 45, 8),
            build_lane("south", 19, 0.74, 38, 10),
            build_lane("east", 4, 0.18, 12, 24),
            build_lane("west", 3, 0.12, 8, 26),
        ],
        phases=default_phases(),
        current_phase="east_west",
        time_in_current_phase_s=18,
    )
    result = DecisionEngine().decide(
        state=state,
        history={"north_south": 24, "east_west": 0},
    )
    assert result.selected_phase == "north_south"
    assert 12 <= result.green_duration_s <= 40


def test_emergency_bonus_can_select_east_west() -> None:
    state = JunctionState(
        lanes=[
            build_lane("north", 10, 0.35, 20, 18),
            build_lane("south", 9, 0.32, 18, 18),
            build_lane("east", 3, 0.10, 8, 26, emergency=True),
            build_lane("west", 4, 0.14, 9, 24),
        ],
        phases=default_phases(),
        current_phase="north_south",
        time_in_current_phase_s=20,
    )
    result = DecisionEngine().decide(
        state=state,
        history={"north_south": 0, "east_west": 6},
    )
    assert result.selected_phase == "east_west"
