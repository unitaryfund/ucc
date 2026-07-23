"""Unit tests for hardware/hardware_metric.py — Phase 2."""

from __future__ import annotations

import pytest
import numpy as np

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.hardware.distances import (
    hop_distance_matrix,
    weighted_distance_matrix,
)


# ---------------------------------------------------------------------------
# Fake coupling map (no Qiskit dependency)
# ---------------------------------------------------------------------------


class FakeCouplingMap:
    def __init__(self, n, edges):
        self._n = n
        self._edges = edges

    def size(self):
        return self._n

    def get_edges(self):
        return list(self._edges)


LINE4_MAP = FakeCouplingMap(4, [(0, 1), (1, 2), (2, 3)])
RING4_MAP = FakeCouplingMap(4, [(0, 1), (1, 2), (2, 3), (3, 0)])


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_from_coupling_map_returns_hardware_metric():
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    assert isinstance(metric, HardwareMetric)


def test_from_coupling_map_no_calibration_data():
    """Should succeed without a Qiskit Target (no calibration available)."""
    metric = HardwareMetric.from_coupling_map(LINE4_MAP, target=None)
    assert metric is not None


# ---------------------------------------------------------------------------
# Distances
# ---------------------------------------------------------------------------


def test_hop_distances_shape():
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    n = LINE4_MAP.size()
    assert len(metric.hop_distances) == n
    for row in metric.hop_distances.values():
        assert len(row) == n


def test_hop_distances_match_standalone_function():
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    # Build the same adjacency independently
    from ucc.custom_passes.spectral.graph import (
        coupling_to_undirected_adjacency,
    )

    adjacency = coupling_to_undirected_adjacency(LINE4_MAP)
    expected = hop_distance_matrix(adjacency)
    assert metric.hop_distances == expected


def test_weighted_distances_match_standalone_function():
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    from ucc.custom_passes.spectral.graph import (
        coupling_to_undirected_adjacency,
    )

    adjacency = coupling_to_undirected_adjacency(LINE4_MAP)
    expected = weighted_distance_matrix(adjacency)
    for i in adjacency:
        for j in adjacency:
            assert metric.weighted_distances[i][j] == pytest.approx(
                expected[i][j]
            )


# ---------------------------------------------------------------------------
# Spectral coordinates
# ---------------------------------------------------------------------------


def test_spectral_coords_shape():
    n_components = 2
    metric = HardwareMetric.from_coupling_map(
        LINE4_MAP, n_components=n_components
    )
    assert metric.spectral_coords.shape == (LINE4_MAP.size(), n_components)


def test_spectral_coords_are_real():
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    assert np.isrealobj(metric.spectral_coords)


# ---------------------------------------------------------------------------
# Curve order
# ---------------------------------------------------------------------------


def test_curve_order_length():
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    assert len(metric.curve_order) == LINE4_MAP.size()


def test_curve_order_is_permutation():
    """Each qubit should have a unique rank."""
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    ranks = list(metric.curve_order.values())
    assert len(set(ranks)) == len(ranks)


def test_curve_rank_lookup():
    metric = HardwareMetric.from_coupling_map(LINE4_MAP)
    for qubit in range(LINE4_MAP.size()):
        rank = metric.curve_rank(qubit)
        assert isinstance(rank, int)
        assert rank >= 0


# ---------------------------------------------------------------------------
# Ring graph
# ---------------------------------------------------------------------------


def test_ring_graph_all_hop_distances_equal_or_less_than_two():
    metric = HardwareMetric.from_coupling_map(RING4_MAP)
    for i, row in metric.hop_distances.items():
        for j, d in row.items():
            if i != j:
                assert d <= 2.0
