"""SWAP candidate scoring: shortest-path, calibration cost, lookahead, curve rank."""

from __future__ import annotations

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.routing_state import RoutingState


def _score_interaction(
    state: RoutingState,
    metric: HardwareMetric,
    gate: tuple[int, int],
) -> float:
    """Score a single logical interaction under the current routing state."""
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


def _spectral_alignment_penalty(
    state: RoutingState,
    metric: HardwareMetric,
) -> float:
    """Score how far the current layout drifted from the reference layout.

    The result is averaged over the number of mapped qubits so the penalty
    stays on a comparable scale regardless of device size, letting it be
    combined with the (per-gate) SABRE score via a fixed weight.
    """
    if not state.logical_to_physical:
        return 0.0
    total = 0.0
    for logical, physical in state.logical_to_physical.items():
        reference_physical = state.reference_layout.get(logical, physical)
        total += abs(
            metric.curve_order.get(physical, physical)
            - metric.curve_order.get(reference_physical, reference_physical)
        )
    return total / len(state.logical_to_physical)


def _base_swap_score(
    state: RoutingState,
    metric: HardwareMetric,
    *,
    lookahead_depth: int,
) -> float:
    """Score the front layer using SABRE-style interaction distance."""
    score = 0.0
    for gate in state.front_layer[:lookahead_depth]:
        score += _score_interaction(state, metric, gate)
    return score


def score_swap(
    state: RoutingState,
    metric: HardwareMetric,
    physical_a: int,
    physical_b: int,
    *,
    lookahead_depth: int = 1,
) -> float:
    """Score a candidate SWAP; lower scores are better.

    Args:
        state: Current routing state.
        metric: Hardware metric used for distance and locality scoring.
        physical_a: First physical qubit in the candidate SWAP.
        physical_b: Second physical qubit in the candidate SWAP.
        lookahead_depth: Number of front-layer gates to include.

    Returns:
        A scalar heuristic score; lower is better.
    """
    trial = RoutingState.from_initial_layout(
        dict(state.logical_to_physical),
        reference_layout=dict(state.reference_layout),
        front_layer=list(state.front_layer),
    )
    trial.swap(physical_a, physical_b)
    return _base_swap_score(trial, metric, lookahead_depth=lookahead_depth)


DEFAULT_SPECTRAL_WEIGHT = 0.25
"""Default weight for the spectral-alignment term in ``spectral_tiebreak_score``.

Set to 0.0 to fully disable spectral scoring and recover plain SABRE
behavior; increase to let spectral locality dominate over hop distance.
"""


def spectral_tiebreak_score(
    state: RoutingState,
    metric: HardwareMetric,
    physical_a: int,
    physical_b: int,
    *,
    lookahead_depth: int = 1,
    spectral_weight: float = DEFAULT_SPECTRAL_WEIGHT,
) -> float:
    """Return a blended SABRE + spectral-locality score for a candidate SWAP.

    Unlike a lexicographic tie-break, the spectral-alignment penalty is
    weighted and added directly to the SABRE distance score, so it
    participates in every routing decision instead of only breaking exact
    ties (which almost never occur with continuous calibration-aware costs).

    Args:
        state: Current routing state.
        metric: Hardware metric used for distance and locality scoring.
        physical_a: First physical qubit in the candidate SWAP.
        physical_b: Second physical qubit in the candidate SWAP.
        lookahead_depth: Number of front-layer gates to include.
        spectral_weight: Weight applied to the spectral-alignment penalty
            relative to the SABRE distance score. Lower is better.

    Returns:
        A scalar heuristic score; lower is better.
    """
    trial = RoutingState.from_initial_layout(
        dict(state.logical_to_physical),
        reference_layout=dict(state.reference_layout),
        front_layer=list(state.front_layer),
    )
    trial.swap(physical_a, physical_b)
    base_score = _base_swap_score(
        trial, metric, lookahead_depth=lookahead_depth
    )
    spectral_penalty = _spectral_alignment_penalty(trial, metric)
    return base_score + spectral_weight * spectral_penalty
