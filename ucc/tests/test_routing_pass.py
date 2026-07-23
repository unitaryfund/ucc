"""Unit tests for ``routing/routing_pass.py``."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.quantum_info import Statevector

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.routing_pass import SpectralRoutingPass


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


def test_routing_pass_uses_layout_from_property_set():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 2)
    dag = circuit_to_dag(circuit)

    pass_ = SpectralRoutingPass()
    pass_.hardware_metric = _metric()
    pass_.property_set["layout"] = {0: 0, 1: 1, 2: 2}
    out_dag = pass_.run(dag)
    routed = dag_to_circuit(out_dag)

    assert routed.count_ops().get("swap", 0) >= 1


def test_routing_pass_stores_final_layout():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 2)
    dag = circuit_to_dag(circuit)

    pass_ = SpectralRoutingPass()
    pass_.hardware_metric = _metric()
    pass_.property_set["layout"] = {0: 0, 1: 1, 2: 2}
    pass_.run(dag)

    assert pass_.property_set["final_layout"] == {0: 0, 1: 1, 2: 2}


def test_routing_pass_preserves_semantics():
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 2)
    circuit.x(1)
    dag = circuit_to_dag(circuit)

    pass_ = SpectralRoutingPass()
    pass_.hardware_metric = _metric()
    pass_.property_set["layout"] = {0: 0, 1: 1, 2: 2}
    out_dag = pass_.run(dag)
    routed = dag_to_circuit(out_dag)

    assert Statevector.from_instruction(circuit).equiv(
        Statevector.from_instruction(routed)
    )
