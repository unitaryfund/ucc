"""Optional integration test against an installed Qiskit SDK."""

from qiskit.transpiler import CouplingMap
from ucc.custom_passes.spectral.graph import coupling_to_undirected_adjacency


def test_real_qiskit_coupling_map():
    coupling = CouplingMap.from_line(4, bidirectional=True)

    adjacency = coupling_to_undirected_adjacency(coupling)

    assert adjacency == {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0},
    }
