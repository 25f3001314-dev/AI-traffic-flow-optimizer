from __future__ import annotations

from dataclasses import dataclass

from .schemas import ControllerWeights, DecisionResponse, JunctionState, PhaseDefinition


@dataclass(slots=True)
class PhaseScore:
    phase: PhaseDefinition
    total_score: float
    congestion_index: float
    breakdown: dict[str, float]


class DecisionEngine:
    def __init__(self, weights: ControllerWeights | None = None) -> None:
        self.weights = weights or ControllerWeights()

    def decide(
        self,
        state: JunctionState,
        history: dict[str, float] | None = None,
    ) -> DecisionResponse:
        history = self._normalized_history(state, history)
        lane_map = {lane.id: lane for lane in state.lanes}
        phase_scores = {
            phase.name: self._score_phase(phase, lane_map, history, state.current_phase)
            for phase in state.phases
        }

        best_phase = max(phase_scores.values(), key=lambda item: item.total_score)
        selected_phase_name = best_phase.phase.name
        reason_parts: list[str] = [
            f"Highest demand pressure is on {best_phase.phase.name} with score {best_phase.total_score:.1f}."
        ]

        phase_map = {phase.name: phase for phase in state.phases}
        emergency_phase_names = [
            phase.name
            for phase in state.phases
            if any(getattr(lane_map.get(lane_id), "emergency_vehicle", False) for lane_id in phase.green_lanes)
        ]
        if emergency_phase_names:
            emergency_best = max(
                (phase_scores[name] for name in emergency_phase_names),
                key=lambda item: item.total_score,
            )
            if state.current_phase and state.current_phase in phase_map:
                current_phase_def = phase_map[state.current_phase]
                if state.time_in_current_phase_s >= current_phase_def.min_green_s or state.current_phase in emergency_phase_names:
                    selected_phase_name = emergency_best.phase.name
                    reason_parts = [
                        f"Emergency priority activated for {emergency_best.phase.name}."
                    ]
            else:
                selected_phase_name = emergency_best.phase.name
                reason_parts = [
                    f"Emergency priority activated for {emergency_best.phase.name}."
                ]

        if state.current_phase and state.current_phase in phase_map and not emergency_phase_names:
            current_phase = phase_scores[state.current_phase]
            current_phase_def = phase_map[state.current_phase]
            competing_scores = [
                value.total_score
                for name, value in phase_scores.items()
                if name != state.current_phase
            ]
            best_other = max(competing_scores) if competing_scores else current_phase.total_score

            if state.time_in_current_phase_s < current_phase_def.min_green_s:
                selected_phase_name = state.current_phase
                reason_parts = [
                    "Current phase is still inside the minimum green window, so switching is blocked."
                ]
            elif (
                current_phase.total_score >= best_other * self.weights.switch_hysteresis
                and state.time_in_current_phase_s < current_phase_def.max_green_s
            ):
                selected_phase_name = state.current_phase
                if state.current_phase == best_phase.phase.name:
                    reason_parts = [
                        "Current phase already has the best score, so it is extended."
                    ]
                else:
                    reason_parts = [
                        "Hysteresis kept the current phase active to avoid rapid oscillation."
                    ]
            else:
                selected_phase_name = best_phase.phase.name
                reason_parts = [
                    f"Switching from {state.current_phase} to {best_phase.phase.name} due to higher pressure."
                ]

        selected_phase = phase_map[selected_phase_name]
        selected_score = phase_scores[selected_phase_name]
        green_duration_s = self._green_duration(selected_phase, selected_score.congestion_index, lane_map)

        next_history = {
            phase.name: (0.0 if phase.name == selected_phase_name else history.get(phase.name, 0.0) + green_duration_s)
            for phase in state.phases
        }

        return DecisionResponse(
            selected_phase=selected_phase_name,
            green_duration_s=green_duration_s,
            scores={name: round(value.total_score, 2) for name, value in phase_scores.items()},
            phase_breakdown={name: value.breakdown for name, value in phase_scores.items()},
            congestion_index=round(selected_score.congestion_index, 3),
            reason=" ".join(reason_parts),
            history=next_history,
        )

    def _normalized_history(
        self,
        state: JunctionState,
        history: dict[str, float] | None,
    ) -> dict[str, float]:
        history = history or {}
        return {phase.name: float(history.get(phase.name, 0.0)) for phase in state.phases}

    def _green_duration(
        self,
        phase: PhaseDefinition,
        congestion_index: float,
        lane_map: dict[str, object],
    ) -> int:
        span = max(0, phase.max_green_s - phase.min_green_s)
        base_duration = phase.min_green_s + round(span * congestion_index)
        emergency_present = any(
            getattr(lane_map.get(lane_id), "emergency_vehicle", False)
            for lane_id in phase.green_lanes
        )
        if emergency_present:
            base_duration = max(base_duration, phase.min_green_s + 8)
        return int(max(phase.min_green_s, min(phase.max_green_s, base_duration)))

    def _score_phase(
        self,
        phase: PhaseDefinition,
        lane_map: dict[str, object],
        history: dict[str, float],
        current_phase: str | None,
    ) -> PhaseScore:
        total_score = 0.0
        lane_breakdown: dict[str, float] = {}
        lane_indices: list[float] = []
        emergency_bonus = 0.0

        for lane_id in phase.green_lanes:
            lane = lane_map.get(lane_id)
            if lane is None:
                continue

            queue_ratio = min(1.0, lane.queue_length / max(self.weights.queue_capacity, 1))
            wait_ratio = min(1.0, lane.waiting_seconds / 90.0)
            speed_penalty_ratio = min(1.0, max(0.0, 30.0 - lane.average_speed_kph) / 30.0)
            congestion_index = (
                0.45 * lane.density
                + 0.30 * queue_ratio
                + 0.20 * wait_ratio
                + 0.05 * speed_penalty_ratio
            )
            lane_indices.append(congestion_index)

            density_score = lane.density * self.weights.density_weight
            queue_score = lane.queue_length * self.weights.queue_weight
            wait_score = lane.waiting_seconds * self.weights.wait_weight
            speed_penalty = max(0.0, 30.0 - lane.average_speed_kph) * self.weights.speed_penalty_weight
            lane_emergency_score = self.weights.emergency_bonus if lane.emergency_vehicle else 0.0
            emergency_bonus = max(emergency_bonus, 0.25 if lane.emergency_vehicle else emergency_bonus)
            lane_total = density_score + queue_score + wait_score + speed_penalty + lane_emergency_score
            lane_breakdown[lane_id] = round(lane_total, 2)
            total_score += lane_total

        starvation_bonus = history.get(phase.name, 0.0) * self.weights.starvation_weight
        continuity_bonus = self.weights.continuity_bonus if phase.name == current_phase else 0.0
        avg_index = sum(lane_indices) / len(lane_indices) if lane_indices else 0.0
        phase_congestion_index = min(1.0, avg_index + emergency_bonus)
        total_score += starvation_bonus + continuity_bonus

        lane_breakdown["starvation_bonus"] = round(starvation_bonus, 2)
        lane_breakdown["continuity_bonus"] = round(continuity_bonus, 2)
        lane_breakdown["congestion_index"] = round(phase_congestion_index, 3)

        return PhaseScore(
            phase=phase,
            total_score=total_score,
            congestion_index=phase_congestion_index,
            breakdown=lane_breakdown,
        )
