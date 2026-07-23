"""Weighted logical interaction graph extracted from a quantum circuit."""

from __future__ import annotations

from typing import TypeAlias

from qiskit.converters import circuit_to_dag

QubitIndex: TypeAlias = int
Adjacency: TypeAlias = dict[QubitIndex, dict[QubitIndex, float]]


def _iter_op_nodes(circuit_or_dag):
    """Yield operation nodes from a circuit or DAG input."""
    if hasattr(circuit_or_dag, "op_nodes"):
        return circuit_or_dag.op_nodes()
    return circuit_to_dag(circuit_or_dag).op_nodes()


def _qubit_index(qubits, qubit) -> int:
    """Return the index of a qubit in a qubit list."""
    return qubits.index(qubit)


def circuit_to_interaction_graph(circuit_or_dag) -> Adjacency:
    """Return a weighted undirected logical-interaction graph.

    Args:
        circuit_or_dag: A ``QuantumCircuit`` or ``DAGCircuit``.

    Returns:
        A weighted undirected interaction graph where repeated two-qubit gates
        accumulate edge weight.

    Notes:
        Every logical qubit in the input is represented as a vertex, even if it
        has no two-qubit interactions.
    """

    qubits = list(getattr(circuit_or_dag, "qubits"))
    graph: Adjacency = {i: {} for i in range(len(qubits))}

    for node in _iter_op_nodes(circuit_or_dag):
        if getattr(getattr(node, "op", None), "name", None) == "barrier":
            continue
        qargs = getattr(node, "qargs", ())
        if len(qargs) != 2:
            continue

        i = _qubit_index(qubits, qargs[0])
        j = _qubit_index(qubits, qargs[1])
        if i == j:
            continue

        graph[i][j] = graph[i].get(j, 0.0) + 1.0
        graph[j][i] = graph[j].get(i, 0.0) + 1.0

    return graph
