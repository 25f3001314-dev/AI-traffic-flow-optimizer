from app.core.simulator import TrafficSimulator
from app.services.preset_loader import get_preset


def test_morning_peak_adaptive_reduces_wait_and_queue() -> None:
    preset = get_preset("morning_peak")
    assert preset is not None
    comparison = TrafficSimulator(preset).run_comparison()
    assert comparison.adaptive.metrics.average_wait_s <= comparison.baseline.metrics.average_wait_s
    assert comparison.adaptive.metrics.max_total_queue <= comparison.baseline.metrics.max_total_queue
    assert len(comparison.adaptive.decisions) > 0
    assert len(comparison.adaptive.timeline) > 0
