"""Spectral curve-rank pairing and layout cost scoring."""

from __future__ import annotations

from typing import TypeAlias

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric

QubitIndex: TypeAlias = int
Placement: TypeAlias = dict[QubitIndex, QubitIndex]


def _sorted_by_curve_rank(metric: HardwareMetric) -> list[int]:
    """Return qubits sorted by curve rank and then by index."""
    return [
        qubit
        for qubit, _ in sorted(
            metric.curve_order.items(), key=lambda item: (item[1], item[0])
        )
    ]


def spectral_placement(
    logical_metric: HardwareMetric, hardware_metric: HardwareMetric
) -> Placement:
    """Pair logical and physical qubits in curve-rank order.

    Args:
        logical_metric: Metric describing the logical interaction graph.
        hardware_metric: Metric describing the hardware graph.

    Returns:
        Logical-to-physical qubit placement.
    """
    logical_order = _sorted_by_curve_rank(logical_metric)
    hardware_order = _sorted_by_curve_rank(hardware_metric)

    placement: Placement = {}
    for logical_qubit, physical_qubit in zip(logical_order, hardware_order):
        placement[logical_qubit] = physical_qubit
    return placement


def layout_cost(
    logical_metric: HardwareMetric,
    hardware_metric: HardwareMetric,
    placement: Placement,
) -> float:
    """Score a placement by weighted logical interactions on hardware distance.

    Args:
        logical_metric: Metric describing the logical interaction graph.
        hardware_metric: Metric describing the hardware graph.
        placement: Logical-to-physical mapping to score.

    Returns:
        Weighted interaction cost; lower is better.
    """
    total = 0.0
    seen: set[tuple[int, int]] = set()

    for source, neighbors in logical_metric.adjacency.items():
        for target, weight in neighbors.items():
            if source == target:
                continue
            edge = tuple(sorted((source, target)))
            if edge in seen:
                continue
            seen.add(edge)

            physical_source = placement[source]
            physical_target = placement[target]
            total += (
                weight
                * hardware_metric.hop_distances[physical_source][
                    physical_target
                ]
            )

    return float(total)
