"""Unit tests for ``layout/logical_graph.py``."""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag

from ucc.custom_passes.spectral.layout.logical_graph import (
    circuit_to_interaction_graph,
)


def test_two_qubit_gates_accumulate_weights():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)
    circuit.cz(1, 0)
    circuit.cx(0, 1)

    graph = circuit_to_interaction_graph(circuit)

    assert graph[0][1] == pytest.approx(3.0)
    assert graph[1][0] == pytest.approx(3.0)


def test_single_qubit_operations_are_ignored():
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.x(1)
    circuit.cx(0, 2)

    graph = circuit_to_interaction_graph(circuit)

    assert graph[0][2] == pytest.approx(1.0)
    assert graph[2][0] == pytest.approx(1.0)
    assert graph[0].get(1, 0.0) == 0.0
    assert graph[1] == {}


def test_all_logical_qubits_are_present():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 1)

    graph = circuit_to_interaction_graph(circuit)

    assert set(graph) == {0, 1, 2, 3}
    assert graph[2] == {}
    assert graph[3] == {}


def test_circuit_and_dag_inputs_match():
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cz(1, 2)
    dag = circuit_to_dag(circuit)

    circuit_graph = circuit_to_interaction_graph(circuit)
    dag_graph = circuit_to_interaction_graph(dag)

    assert dag_graph == circuit_graph


def test_barriers_do_not_affect_graph():
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    circuit.barrier()
    circuit.cx(0, 1)

    graph = circuit_to_interaction_graph(circuit)

    assert graph[0][1] == pytest.approx(2.0)
    assert graph[1][0] == pytest.approx(2.0)
