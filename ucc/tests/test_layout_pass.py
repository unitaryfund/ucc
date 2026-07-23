"""Unit tests for ``layout/layout_pass.py``."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.layout.layout_pass import SpectralLayoutPass


def _metric(curve_order):
    adjacency = {i: {} for i in curve_order}
    distances = {
        i: {j: (0.0 if i == j else 1.0) for j in curve_order}
        for i in curve_order
    }
    return HardwareMetric(
        adjacency=adjacency,
        hop_distances=distances,
        weighted_distances=distances,
        spectral_coords=object(),
        curve_order=curve_order,
    )


def test_layout_pass_stores_layout_in_property_set():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    dag = circuit_to_dag(circuit)
    hardware_metric = _metric({0: 2, 1: 0, 2: 1})

    layout_pass = SpectralLayoutPass()
    layout_pass.hardware_metric = hardware_metric
    layout_pass.run(dag)

    assert layout_pass.property_set["layout"] == {0: 1, 1: 2, 2: 0}


def test_layout_pass_uses_logical_interaction_graph():
    circuit = QuantumCircuit(4)
    circuit.cx(2, 3)
    circuit.cx(0, 1)
    dag = circuit_to_dag(circuit)
    hardware_metric = _metric({0: 0, 1: 1, 2: 2, 3: 3})

    layout_pass = SpectralLayoutPass()
    layout_pass.hardware_metric = hardware_metric
    layout_pass.run(dag)

    assert set(layout_pass.property_set["layout"]) == {0, 1, 2, 3}


def test_layout_pass_is_deterministic_for_same_input():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 2)
    circuit.cx(0, 1)
    dag = circuit_to_dag(circuit)
    hardware_metric = _metric({0: 1, 1: 0, 2: 2})

    first = SpectralLayoutPass()
    second = SpectralLayoutPass()
    first.hardware_metric = hardware_metric
    second.hardware_metric = hardware_metric

    first.run(dag)
    second.run(dag)

    assert first.property_set["layout"] == second.property_set["layout"]
