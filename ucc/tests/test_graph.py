"""Unit tests for Phase 1 hardware-graph construction."""

from __future__ import annotations

from dataclasses import dataclass

from pytest import fixture, mark, raises, approx
from ucc.custom_passes.spectral.graph import coupling_to_undirected_adjacency


@dataclass(frozen=True)
class FakeCouplingMap:
    """Small duck-typed replacement for Qiskit's CouplingMap in unit tests."""

    number_of_qubits: int
    edges: tuple[tuple[int, int], ...]

    def size(self) -> int:
        return self.number_of_qubits

    def get_edges(self):
        return list(self.edges)


@fixture
def line4() -> FakeCouplingMap:
    return FakeCouplingMap(
        4,
        (
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (2, 3),
            (3, 2),
        ),
    )


def test_line_graph_matches_expected_adjacency(line4):
    adjacency = coupling_to_undirected_adjacency(line4)

    assert adjacency == {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0},
    }


def test_adjacency_is_symmetric(line4):
    adjacency = coupling_to_undirected_adjacency(line4)

    for source, neighbors in adjacency.items():
        for destination, weight in neighbors.items():
            assert adjacency[destination][source] == weight


def test_directed_duplicates_are_collapsed(line4):
    adjacency = coupling_to_undirected_adjacency(line4)

    assert list(adjacency[0]) == [1]
    assert list(adjacency[1]) == [0, 2]


def test_all_physical_qubits_are_present_including_isolated_ones():
    coupling = FakeCouplingMap(4, ((0, 1),))

    adjacency = coupling_to_undirected_adjacency(coupling)

    assert set(adjacency) == {0, 1, 2, 3}
    assert adjacency[2] == {}
    assert adjacency[3] == {}


def test_one_direction_is_made_undirected():
    coupling = FakeCouplingMap(2, ((0, 1),))

    adjacency = coupling_to_undirected_adjacency(coupling)

    assert adjacency == {
        0: {1: 1.0},
        1: {0: 1.0},
    }


def test_custom_uniform_edge_weight_is_applied():
    coupling = FakeCouplingMap(2, ((0, 1),))

    adjacency = coupling_to_undirected_adjacency(
        coupling,
        edge_weight=2.5,
    )

    assert adjacency[0][1] == approx(2.5)
    assert adjacency[1][0] == approx(2.5)


@mark.parametrize("edge_weight", [0.0, -1.0])
def test_non_positive_edge_weight_raises(edge_weight):
    coupling = FakeCouplingMap(2, ((0, 1),))

    with raises(ValueError, match="positive"):
        coupling_to_undirected_adjacency(
            coupling,
            edge_weight=edge_weight,
        )


def test_out_of_range_endpoint_raises():
    coupling = FakeCouplingMap(2, ((0, 2),))

    with raises(ValueError, match="outside the valid range"):
        coupling_to_undirected_adjacency(coupling)


def test_negative_endpoint_raises():
    coupling = FakeCouplingMap(2, ((-1, 1),))

    with raises(ValueError, match="outside the valid range"):
        coupling_to_undirected_adjacency(coupling)


def test_self_loop_raises():
    coupling = FakeCouplingMap(2, ((1, 1),))

    with raises(ValueError, match="Self-loop"):
        coupling_to_undirected_adjacency(coupling)


def test_non_integer_endpoint_raises():
    coupling = FakeCouplingMap(2, ((0, 1.5),))

    with raises(TypeError, match="must be an integer"):
        coupling_to_undirected_adjacency(coupling)


def test_malformed_edge_raises():
    coupling = FakeCouplingMap(2, ((0, 1, 2),))  # type: ignore[arg-type]

    with raises(ValueError, match="exactly two endpoints"):
        coupling_to_undirected_adjacency(coupling)


def test_empty_coupling_map_returns_empty_adjacency():
    coupling = FakeCouplingMap(0, ())

    assert coupling_to_undirected_adjacency(coupling) == {}
