from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from itertools import islice

import numpy as np

from .decision_engine import DecisionEngine
from .schemas import (
    ControllerWeights,
    DecisionEvent,
    ImprovementSummary,
    JunctionState,
    LaneState,
    SimulationComparison,
    SimulationMetrics,
    SimulationRequest,
    SimulationRun,
    TimelinePoint,
)


@dataclass(slots=True)
class Vehicle:
    arrival_s: int
    emergency: bool = False


@dataclass(slots=True)
class LaneRuntime:
    vehicles: deque[Vehicle] = field(default_factory=deque)
    service_credit: float = 0.0


class TrafficSimulator:
    def __init__(self, request: SimulationRequest) -> None:
        self.request = request
        self.phase_map = {phase.name: phase for phase in request.phases}
        self.lane_ids = [profile.lane_id for profile in request.profiles]
        self.arrival_schedule = self._generate_arrival_schedule()

    def run_comparison(self) -> SimulationComparison:
        baseline = self._run_controller(controller_name="baseline")
        adaptive = self._run_controller(controller_name="adaptive")
        improvements = self._compare_runs(baseline.metrics, adaptive.metrics)
        return SimulationComparison(
            scenario_name=self.request.name,
            scenario_description=self.request.description,
            baseline=baseline,
            adaptive=adaptive,
            improvements=improvements,
        )

    def _generate_arrival_schedule(self) -> list[dict[str, list[bool]]]:
        config = self.request.config
        rng = np.random.default_rng(config.random_seed)
        schedule: list[dict[str, list[bool]]] = [
            {lane_id: [] for lane_id in self.lane_ids} for _ in range(config.duration_s)
        ]

        for t in range(config.duration_s):
            for profile in self.request.profiles:
                segment = next(
                    (item for item in profile.segments if item.start_s <= t < item.end_s),
                    None,
                )
                if segment is None:
                    continue
                arrival_lambda = segment.arrival_rate_vph / 3600.0
                arrival_count = int(rng.poisson(arrival_lambda))
                emergencies = [
                    bool(rng.random() < segment.emergency_probability)
                    for _ in range(arrival_count)
                ]
                schedule[t][profile.lane_id].extend(emergencies)
        return schedule

    def _build_state(
        self,
        lanes_runtime: dict[str, LaneRuntime],
        active_phase: str | None,
        time_in_current_phase_s: int,
        current_time_s: int,
    ) -> JunctionState:
        lane_states: list[LaneState] = []
        for lane_id in self.lane_ids:
            runtime = lanes_runtime[lane_id]
            queue_length = len(runtime.vehicles)
            density = min(1.0, queue_length / max(self.request.config.queue_capacity, 1))
            waiting_seconds = 0.0
            if runtime.vehicles:
                waiting_seconds = float(max(0, current_time_s - runtime.vehicles[0].arrival_s))
            emergency_vehicle = any(vehicle.emergency for vehicle in islice(runtime.vehicles, 3))
            average_speed_kph = max(4.0, 35.0 * (1.0 - density * 0.85))
            lane_states.append(
                LaneState(
                    id=lane_id,
                    queue_length=queue_length,
                    density=round(density, 3),
                    average_speed_kph=round(average_speed_kph, 2),
                    waiting_seconds=round(waiting_seconds, 2),
                    emergency_vehicle=emergency_vehicle,
                )
            )
        return JunctionState(
            lanes=lane_states,
            phases=self.request.phases,
            current_phase=active_phase,
            time_in_current_phase_s=time_in_current_phase_s,
        )

    def _run_controller(self, controller_name: str) -> SimulationRun:
        config = self.request.config
        weights = ControllerWeights(queue_capacity=config.queue_capacity)
        decision_engine = DecisionEngine(weights=weights)
        lanes_runtime = {lane_id: LaneRuntime() for lane_id in self.lane_ids}
        history = {phase.name: 0.0 for phase in self.request.phases}

        total_arrivals = 0
        dropped_arrivals = 0
        total_departed = 0
        wait_samples: list[float] = []
        queue_samples: list[int] = []
        total_idle_vehicle_seconds = 0.0
        timeline: list[TimelinePoint] = []
        decisions: list[DecisionEvent] = []

        active_phase: str | None = None
        pending_phase: str | None = None
        pending_green = 0
        green_remaining = 0
        transition_remaining = 0
        stage = "idle"
        time_in_current_green = 0
        baseline_cycle_index = 0

        for t in range(config.duration_s):
            if active_phase is None and pending_phase is not None and transition_remaining <= 0:
                active_phase = pending_phase
                green_remaining = pending_green
                pending_phase = None
                pending_green = 0
                stage = "green"
                time_in_current_green = 0

            if active_phase is None and pending_phase is None and green_remaining <= 0 and transition_remaining <= 0:
                if controller_name == "baseline":
                    phase = self.request.phases[baseline_cycle_index % len(self.request.phases)]
                    active_phase = phase.name
                    green_remaining = config.baseline_fixed_green_s
                    stage = "green"
                    time_in_current_green = 0
                    decisions.append(
                        DecisionEvent(
                            t=t,
                            selected_phase=phase.name,
                            green_duration_s=config.baseline_fixed_green_s,
                            reason="Fixed-time baseline selected the next phase in sequence.",
                            scores={phase.name: 1.0},
                        )
                    )
                else:
                    state = self._build_state(lanes_runtime, None, 0, t)
                    decision = decision_engine.decide(state=state, history=history)
                    active_phase = decision.selected_phase
                    green_remaining = decision.green_duration_s
                    stage = "green"
                    time_in_current_green = 0
                    decisions.append(
                        DecisionEvent(
                            t=t,
                            selected_phase=decision.selected_phase,
                            green_duration_s=decision.green_duration_s,
                            reason=decision.reason,
                            scores=decision.scores,
                        )
                    )

            for lane_id, emergency_flags in self.arrival_schedule[t].items():
                total_arrivals += len(emergency_flags)
                for emergency in emergency_flags:
                    runtime = lanes_runtime[lane_id]
                    if len(runtime.vehicles) >= config.queue_capacity:
                        dropped_arrivals += 1
                        continue
                    runtime.vehicles.append(Vehicle(arrival_s=t, emergency=emergency))

            green_lanes = set()
            display_phase = active_phase or pending_phase
            if stage == "green" and active_phase is not None:
                green_lanes = set(self.phase_map[active_phase].green_lanes)

            second_departures = 0
            for lane_id, runtime in lanes_runtime.items():
                if lane_id in green_lanes:
                    runtime.service_credit = min(2.0, runtime.service_credit + config.saturation_flow_vps)
                    while runtime.service_credit >= 1.0 and runtime.vehicles:
                        vehicle = runtime.vehicles.popleft()
                        runtime.service_credit -= 1.0
                        second_departures += 1
                        total_departed += 1
                        wait_samples.append(float(max(0, t - vehicle.arrival_s)))
                else:
                    runtime.service_credit = 0.0

            total_queue = sum(len(runtime.vehicles) for runtime in lanes_runtime.values())
            total_idle_vehicle_seconds += float(total_queue)
            queue_samples.append(total_queue)

            if t % config.sample_step_s == 0 or t == config.duration_s - 1:
                densities = {
                    lane_id: round(
                        min(1.0, len(runtime.vehicles) / max(config.queue_capacity, 1)),
                        3,
                    )
                    for lane_id, runtime in lanes_runtime.items()
                }
                timeline.append(
                    TimelinePoint(
                        t=t,
                        phase=display_phase,
                        stage=stage,
                        queue_lengths={
                            lane_id: len(runtime.vehicles)
                            for lane_id, runtime in lanes_runtime.items()
                        },
                        densities=densities,
                        throughput=total_departed,
                        avg_wait_s=round(float(np.mean(wait_samples)) if wait_samples else 0.0, 2),
                    )
                )

            for phase_name in history:
                if stage == "green" and phase_name == active_phase:
                    history[phase_name] = 0.0
                else:
                    history[phase_name] += 1.0

            if stage == "green":
                green_remaining -= 1
                time_in_current_green += 1
                if green_remaining <= 0:
                    if controller_name == "baseline":
                        baseline_cycle_index = (baseline_cycle_index + 1) % len(self.request.phases)
                        next_phase = self.request.phases[baseline_cycle_index]
                        pending_phase = next_phase.name
                        pending_green = config.baseline_fixed_green_s
                        transition_remaining = next_phase.amber_s + next_phase.all_red_s
                        active_phase = None
                        stage = "transition" if transition_remaining > 0 else "idle"
                        time_in_current_green = 0
                        decisions.append(
                            DecisionEvent(
                                t=t + 1,
                                selected_phase=next_phase.name,
                                green_duration_s=config.baseline_fixed_green_s,
                                reason="Baseline cycled to the next phase after fixed green elapsed.",
                                scores={next_phase.name: 1.0},
                            )
                        )
                    else:
                        state = self._build_state(
                            lanes_runtime=lanes_runtime,
                            active_phase=active_phase,
                            time_in_current_phase_s=time_in_current_green,
                            current_time_s=t,
                        )
                        decision = decision_engine.decide(state=state, history=history)
                        if decision.selected_phase == active_phase:
                            green_remaining = decision.green_duration_s
                            time_in_current_green = 0
                            decisions.append(
                                DecisionEvent(
                                    t=t + 1,
                                    selected_phase=decision.selected_phase,
                                    green_duration_s=decision.green_duration_s,
                                    reason=decision.reason,
                                    scores=decision.scores,
                                )
                            )
                        else:
                            pending_phase = decision.selected_phase
                            pending_green = decision.green_duration_s
                            transition_remaining = (
                                self.phase_map[pending_phase].amber_s
                                + self.phase_map[pending_phase].all_red_s
                            )
                            active_phase = None
                            stage = "transition" if transition_remaining > 0 else "idle"
                            time_in_current_green = 0
                            decisions.append(
                                DecisionEvent(
                                    t=t + 1,
                                    selected_phase=decision.selected_phase,
                                    green_duration_s=decision.green_duration_s,
                                    reason=decision.reason,
                                    scores=decision.scores,
                                )
                            )
            elif stage == "transition":
                transition_remaining -= 1
                if transition_remaining <= 0:
                    stage = "idle"

        idle_fuel_l = (total_idle_vehicle_seconds / 3600.0) * config.idle_fuel_lph
        metrics = SimulationMetrics(
            total_arrivals=total_arrivals,
            dropped_arrivals=dropped_arrivals,
            throughput=total_departed,
            average_wait_s=round(float(np.mean(wait_samples)) if wait_samples else 0.0, 2),
            p95_wait_s=round(float(np.percentile(wait_samples, 95)) if wait_samples else 0.0, 2),
            max_total_queue=int(max(queue_samples) if queue_samples else 0),
            mean_total_queue=round(float(np.mean(queue_samples)) if queue_samples else 0.0, 2),
            total_idle_vehicle_seconds=round(total_idle_vehicle_seconds, 2),
            estimated_idle_fuel_l=round(idle_fuel_l, 3),
            estimated_co2_kg=round(idle_fuel_l * 2.31, 3),
        )
        return SimulationRun(
            controller_name=controller_name,
            metrics=metrics,
            timeline=timeline,
            decisions=decisions,
        )

    def _compare_runs(
        self,
        baseline: SimulationMetrics,
        adaptive: SimulationMetrics,
    ) -> ImprovementSummary:
        return ImprovementSummary(
            wait_time_reduction_pct=self._pct_down(baseline.average_wait_s, adaptive.average_wait_s),
            throughput_improvement_pct=self._pct_up(baseline.throughput, adaptive.throughput),
            max_queue_reduction_pct=self._pct_down(baseline.max_total_queue, adaptive.max_total_queue),
            co2_reduction_pct=self._pct_down(baseline.estimated_co2_kg, adaptive.estimated_co2_kg),
        )

    @staticmethod
    def _pct_down(old: float, new: float) -> float:
        if old <= 0:
            return 0.0
        return round(((old - new) / old) * 100.0, 2)

    @staticmethod
    def _pct_up(old: float, new: float) -> float:
        if old <= 0:
            return 0.0
        return round(((new - old) / old) * 100.0, 2)
