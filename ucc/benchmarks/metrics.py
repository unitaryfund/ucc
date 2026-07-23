"""Benchmark result summaries and circuit-comparison helpers."""

from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Summary of a benchmark circuit before and after compilation."""

    name: str
    num_qubits: int
    depth_before: int
    depth_after: int
    two_qubit_before: int
    two_qubit_after: int
    swap_after: int
    equivalent: bool


def _bind_parameters(circuit: QuantumCircuit) -> QuantumCircuit:
    """Bind circuit parameters deterministically when needed."""
    if not circuit.parameters:
        return circuit

    ordered_parameters = sorted(
        circuit.parameters, key=lambda parameter: parameter.name
    )
    assignments = {
        parameter: 0.1 + 0.2 * index
        for index, parameter in enumerate(ordered_parameters)
    }
    return circuit.assign_parameters(assignments, inplace=False)


def _two_qubit_gate_count(circuit: QuantumCircuit) -> int:
    """Count all two-qubit gates in a circuit."""
    return sum(
        1
        for instruction in circuit.data
        if instruction.operation.num_qubits == 2
    )


def benchmark_result(
    original,
    compiled,
    *,
    name: str = "benchmark",
) -> BenchmarkResult:
    """Compute a compact summary for a benchmark run.

    Args:
        original: Pre-compiled circuit.
        compiled: Post-compiled circuit.
        name: Benchmark label.

    Returns:
        A ``BenchmarkResult`` with depth, two-qubit count, SWAP count, and
        semantic-equivalence status.
    """
    original = _bind_parameters(original)
    compiled = _bind_parameters(compiled)

    return BenchmarkResult(
        name=name,
        num_qubits=original.num_qubits,
        depth_before=original.depth(),
        depth_after=compiled.depth(),
        two_qubit_before=_two_qubit_gate_count(original),
        two_qubit_after=_two_qubit_gate_count(compiled),
        swap_after=compiled.count_ops().get("swap", 0),
        equivalent=Statevector.from_instruction(original).equiv(
            Statevector.from_instruction(compiled)
        ),
    )
