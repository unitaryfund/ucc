"""Unit tests for hardware/distances.py — Phase 2."""

from __future__ import annotations

import pytest
from ucc.custom_passes.spectral.hardware.distances import (
    hop_distance_matrix,
    weighted_distance_matrix,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def line4():
    """Unweighted 4-qubit line graph: 0-1-2-3."""
    return {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0},
    }


@pytest.fixture
def weighted_line4():
    """Weighted 4-qubit line graph with non-uniform edge costs."""
    return {
        0: {1: 1.0},
        1: {0: 1.0, 2: 3.0},
        2: {1: 3.0, 3: 1.0},
        3: {2: 1.0},
    }


@pytest.fixture
def disconnected():
    """Two disconnected components: {0,1} and {2,3}."""
    return {
        0: {1: 1.0},
        1: {0: 1.0},
        2: {3: 1.0},
        3: {2: 1.0},
    }


# ---------------------------------------------------------------------------
# hop_distance_matrix
# ---------------------------------------------------------------------------


def test_hop_self_distance_is_zero(line4):
    matrix = hop_distance_matrix(line4)
    for node in line4:
        assert matrix[node][node] == 0.0


def test_hop_adjacent_nodes_have_distance_one(line4):
    matrix = hop_distance_matrix(line4)
    assert matrix[0][1] == 1.0
    assert matrix[1][0] == 1.0


def test_hop_line_graph_distances(line4):
    matrix = hop_distance_matrix(line4)
    assert matrix[0][2] == 2.0
    assert matrix[0][3] == 3.0
    assert matrix[1][3] == 2.0


def test_hop_matrix_is_symmetric(line4):
    matrix = hop_distance_matrix(line4)
    for i in line4:
        for j in line4:
            assert matrix[i][j] == matrix[j][i]


def test_hop_disconnected_pair_is_inf(disconnected):
    matrix = hop_distance_matrix(disconnected)
    assert matrix[0][2] == float("inf")
    assert matrix[1][3] == float("inf")


def test_hop_connected_pair_in_disconnected_graph(disconnected):
    matrix = hop_distance_matrix(disconnected)
    assert matrix[0][1] == 1.0
    assert matrix[2][3] == 1.0


def test_hop_single_node():
    adjacency = {0: {}}
    matrix = hop_distance_matrix(adjacency)
    assert matrix[0][0] == 0.0


def test_hop_empty_graph():
    assert hop_distance_matrix({}) == {}


def test_hop_all_nodes_present_in_matrix(line4):
    matrix = hop_distance_matrix(line4)
    assert set(matrix.keys()) == set(line4.keys())
    for row in matrix.values():
        assert set(row.keys()) == set(line4.keys())


# ---------------------------------------------------------------------------
# weighted_distance_matrix
# ---------------------------------------------------------------------------


def test_weighted_self_distance_is_zero(weighted_line4):
    matrix = weighted_distance_matrix(weighted_line4)
    for node in weighted_line4:
        assert matrix[node][node] == 0.0


def test_weighted_adjacent_cost_matches_edge_weight(weighted_line4):
    matrix = weighted_distance_matrix(weighted_line4)
    assert matrix[0][1] == pytest.approx(1.0)
    assert matrix[1][2] == pytest.approx(3.0)


def test_weighted_shortest_path_avoids_expensive_edge(weighted_line4):
    # 0→1→2 costs 1+3=4, while no direct edge exists;
    # 0→3 via 0→1→2→3 costs 1+3+1=5
    matrix = weighted_distance_matrix(weighted_line4)
    assert matrix[0][3] == pytest.approx(5.0)


def test_weighted_matrix_is_symmetric(weighted_line4):
    matrix = weighted_distance_matrix(weighted_line4)
    for i in weighted_line4:
        for j in weighted_line4:
            assert matrix[i][j] == pytest.approx(matrix[j][i])


def test_weighted_disconnected_pair_is_inf(disconnected):
    matrix = weighted_distance_matrix(disconnected)
    assert matrix[0][2] == float("inf")
    assert matrix[1][3] == float("inf")


def test_weighted_single_node():
    adjacency = {0: {}}
    matrix = weighted_distance_matrix(adjacency)
    assert matrix[0][0] == 0.0


def test_weighted_empty_graph():
    assert weighted_distance_matrix({}) == {}


def test_weighted_uniform_costs_match_hop_distances(line4):
    """With uniform edge weight=1, weighted distances equal hop distances."""
    hop = hop_distance_matrix(line4)
    weighted = weighted_distance_matrix(line4)
    for i in line4:
        for j in line4:
            assert weighted[i][j] == pytest.approx(hop[i][j])
