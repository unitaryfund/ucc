"""SWAP candidate scoring: shortest-path, calibration cost, lookahead, curve rank."""

from __future__ import annotations

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.routing_state import RoutingState


def _score_interaction(
    state: RoutingState,
    metric: HardwareMetric,
    gate: tuple[int, int],
) -> float:
    logical_a, logical_b = gate
    physical_a = state.physical_of(logical_a)
    physical_b = state.physical_of(logical_b)
    hop = metric.hop_distances[physical_a][physical_b]
    weighted = metric.weighted_distances[physical_a][physical_b]
    curve_penalty = abs(
        metric.curve_order.get(physical_a, 0)
        - metric.curve_order.get(physical_b, 0)
    )
    return hop + 0.1 * weighted + 0.01 * curve_penalty


def score_swap(
    state: RoutingState,
    metric: HardwareMetric,
    physical_a: int,
    physical_b: int,
    *,
    lookahead_depth: int = 1,
) -> float:
    """Score a candidate SWAP; lower scores are better."""
    trial = RoutingState.from_initial_layout(
        dict(state.logical_to_physical), front_layer=list(state.front_layer)
    )
    trial.swap(physical_a, physical_b)

    score = 0.0
    for gate in trial.front_layer[:lookahead_depth]:
        score += _score_interaction(trial, metric, gate)
    return score
