"""Unit tests for ``layout/placement.py``."""

from __future__ import annotations

import pytest

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.layout.placement import (
    layout_cost,
    spectral_placement,
)


class FakeCouplingMap:
    def __init__(self, n, edges):
        self._n = n
        self._edges = edges

    def size(self):
        return self._n

    def get_edges(self):
        return list(self._edges)


def _metric_with_manual_curve_order() -> HardwareMetric:
    adjacency = {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0},
    }
    hop_distances = {
        0: {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        1: {0: 1.0, 1: 0.0, 2: 1.0, 3: 2.0},
        2: {0: 2.0, 1: 1.0, 2: 0.0, 3: 1.0},
        3: {0: 3.0, 1: 2.0, 2: 1.0, 3: 0.0},
    }
    return HardwareMetric(
        adjacency=adjacency,
        hop_distances=hop_distances,
        weighted_distances=hop_distances,
        spectral_coords=object(),
        curve_order={0: 2, 1: 0, 2: 3, 3: 1},
    )


def test_spectral_placement_pairs_by_curve_rank():
    logical_metric = HardwareMetric(
        adjacency={0: {1: 1.0}, 1: {0: 1.0}, 2: {}},
        hop_distances={
            0: {0: 0.0, 1: 1.0, 2: float("inf")},
            1: {0: 1.0, 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        weighted_distances={
            0: {0: 0.0, 1: 1.0, 2: float("inf")},
            1: {0: 1.0, 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        spectral_coords=object(),
        curve_order={0: 1, 1: 0, 2: 2},
    )
    hardware_metric = _metric_with_manual_curve_order()

    placement = spectral_placement(logical_metric, hardware_metric)

    assert placement == {1: 1, 0: 3, 2: 0}


def test_spectral_placement_uses_sorted_qubits_when_curve_ranks_tie():
    logical_metric = HardwareMetric(
        adjacency={0: {}, 1: {}, 2: {}},
        hop_distances={
            0: {0: 0.0, 1: float("inf"), 2: float("inf")},
            1: {0: float("inf"), 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        weighted_distances={
            0: {0: 0.0, 1: float("inf"), 2: float("inf")},
            1: {0: float("inf"), 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        spectral_coords=object(),
        curve_order={0: 0, 1: 0, 2: 0},
    )
    hardware_metric = HardwareMetric(
        adjacency={0: {}, 1: {}, 2: {}},
        hop_distances={
            0: {0: 0.0, 1: float("inf"), 2: float("inf")},
            1: {0: float("inf"), 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        weighted_distances={
            0: {0: 0.0, 1: float("inf"), 2: float("inf")},
            1: {0: float("inf"), 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        spectral_coords=object(),
        curve_order={0: 1, 1: 1, 2: 1},
    )

    placement = spectral_placement(logical_metric, hardware_metric)

    assert placement == {0: 0, 1: 1, 2: 2}


def test_layout_cost_uses_logical_weights_and_hardware_distance():
    logical_metric = HardwareMetric(
        adjacency={0: {1: 2.0}, 1: {0: 2.0}, 2: {}},
        hop_distances={
            0: {0: 0.0, 1: 1.0, 2: float("inf")},
            1: {0: 1.0, 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        weighted_distances={
            0: {0: 0.0, 1: 1.0, 2: float("inf")},
            1: {0: 1.0, 1: 0.0, 2: float("inf")},
            2: {0: float("inf"), 1: float("inf"), 2: 0.0},
        },
        spectral_coords=object(),
        curve_order={0: 0, 1: 1, 2: 2},
    )
    hardware_metric = _metric_with_manual_curve_order()
    placement = {0: 0, 1: 2, 2: 3}

    cost = layout_cost(logical_metric, hardware_metric, placement)

    assert cost == pytest.approx(4.0)


def test_layout_cost_is_zero_for_empty_logical_graph():
    logical_metric = HardwareMetric(
        adjacency={0: {}, 1: {}},
        hop_distances={
            0: {0: 0.0, 1: float("inf")},
            1: {0: float("inf"), 1: 0.0},
        },
        weighted_distances={
            0: {0: 0.0, 1: float("inf")},
            1: {0: float("inf"), 1: 0.0},
        },
        spectral_coords=object(),
        curve_order={0: 0, 1: 1},
    )
    hardware_metric = HardwareMetric(
        adjacency={0: {}, 1: {}},
        hop_distances={0: {0: 0.0, 1: 1.0}, 1: {0: 1.0, 1: 0.0}},
        weighted_distances={0: {0: 0.0, 1: 1.0}, 1: {0: 1.0, 1: 0.0}},
        spectral_coords=object(),
        curve_order={0: 0, 1: 1},
    )

    assert layout_cost(logical_metric, hardware_metric, {0: 0, 1: 1}) == 0.0
