"""Benchmark result summaries and circuit-comparison helpers."""

from __future__ import annotations

from dataclasses import dataclass

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
    return BenchmarkResult(
        name=name,
        num_qubits=original.num_qubits,
        depth_before=original.depth(),
        depth_after=compiled.depth(),
        two_qubit_before=original.count_ops().get("cx", 0),
        two_qubit_after=compiled.count_ops().get("cx", 0),
        swap_after=compiled.count_ops().get("swap", 0),
        equivalent=Statevector.from_instruction(original).equiv(
            Statevector.from_instruction(compiled)
        ),
    )
