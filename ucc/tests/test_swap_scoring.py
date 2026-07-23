"""Unit tests for ``routing/swap_scoring.py``."""

from __future__ import annotations

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.routing_state import RoutingState
from ucc.custom_passes.spectral.routing.swap_scoring import (
    score_swap,
    spectral_tiebreak_score,
)


def _metric():
    adjacency = {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0},
    }
    distances = {
        0: {0: 0.0, 1: 1.0, 2: 2.0},
        1: {0: 1.0, 1: 0.0, 2: 1.0},
        2: {0: 2.0, 1: 1.0, 2: 0.0},
    }
    return HardwareMetric(
        adjacency=adjacency,
        hop_distances=distances,
        weighted_distances=distances,
        spectral_coords=object(),
        curve_order={0: 0, 1: 1, 2: 2},
    )


def test_swap_that_reduces_front_gate_distance_scores_lower():
    state = RoutingState.from_initial_layout(
        {0: 0, 1: 2, 2: 1}, front_layer=[(0, 1)]
    )
    metric = _metric()

    better = score_swap(state, metric, 1, 2)
    worse = score_swap(state, metric, 0, 2)

    assert better < worse


def test_scoring_is_deterministic_for_same_input():
    state = RoutingState.from_initial_layout(
        {0: 0, 1: 2, 2: 1}, front_layer=[(0, 1), (1, 2)]
    )
    metric = _metric()

    first = score_swap(state, metric, 1, 2)
    second = score_swap(state, metric, 1, 2)

    assert first == second


def test_lookahead_can_distinguish_candidate_swaps():
    state = RoutingState.from_initial_layout(
        {0: 0, 1: 2, 2: 1}, front_layer=[(0, 1), (1, 2)]
    )
    metric = _metric()

    good = score_swap(state, metric, 1, 2, lookahead_depth=2)
    bad = score_swap(state, metric, 0, 1, lookahead_depth=2)

    assert good < bad


def test_spectral_tiebreak_prefers_layouts_closer_to_reference():
    state = RoutingState.from_initial_layout(
        {0: 0, 1: 1, 2: 2}, front_layer=[]
    )
    metric = _metric()

    better = spectral_tiebreak_score(state, metric, 0, 1)
    worse = spectral_tiebreak_score(state, metric, 0, 2)

    assert better < worse
