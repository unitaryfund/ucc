"""Circuit-family generators for benchmark workloads."""

from __future__ import annotations

from qiskit.circuit.library import (
    DraperQFTAdder,
    EfficientSU2,
    QAOAAnsatz,
    QFT,
    RealAmplitudes,
)
from qiskit.circuit.random import random_circuit
from qiskit.quantum_info import SparsePauliOp


def random_benchmark_circuit(
    num_qubits: int,
    depth: int,
    *,
    seed: int | None = None,
    max_operands: int = 2,
):
    """Generate a random circuit benchmark.

    Args:
        num_qubits: Number of qubits.
        depth: Random circuit depth.
        seed: Random seed.
        max_operands: Maximum number of operands per gate.

    Returns:
        A randomized benchmark circuit.
    """
    return random_circuit(
        num_qubits=num_qubits,
        depth=depth,
        max_operands=max_operands,
        measure=False,
        conditional=False,
        reset=False,
        seed=seed,
    )


def qft_benchmark(
    num_qubits: int,
    *,
    approximation_degree: int = 0,
    do_swaps: bool = False,
    insert_barriers: bool = False,
):
    """Generate a QFT benchmark circuit."""
    return QFT(
        num_qubits=num_qubits,
        approximation_degree=approximation_degree,
        do_swaps=do_swaps,
        insert_barriers=insert_barriers,
    )


def efficient_su2_benchmark(
    num_qubits: int,
    *,
    reps: int = 3,
    entanglement: str = "reverse_linear",
):
    """Generate an EfficientSU2 benchmark circuit."""
    return EfficientSU2(
        num_qubits=num_qubits,
        reps=reps,
        entanglement=entanglement,
        flatten=True,
    )


def real_amplitudes_benchmark(
    num_qubits: int,
    *,
    reps: int = 3,
    entanglement: str = "reverse_linear",
):
    """Generate a RealAmplitudes benchmark circuit."""
    return RealAmplitudes(
        num_qubits=num_qubits,
        reps=reps,
        entanglement=entanglement,
        flatten=True,
    )


def qaoa_ring_benchmark(
    num_qubits: int,
    *,
    reps: int = 1,
):
    """Generate a QAOA benchmark over a ring MaxCut cost operator."""
    terms = []
    for i in range(num_qubits):
        j = (i + 1) % num_qubits
        paulis = ["I"] * num_qubits
        paulis[i] = "Z"
        paulis[j] = "Z"
        terms.append(("".join(paulis), 1.0))
    cost_operator = SparsePauliOp.from_list(terms)
    return QAOAAnsatz(cost_operator=cost_operator, reps=reps, flatten=True)


def draper_adder_benchmark(num_state_qubits: int):
    """Generate a Draper QFT adder benchmark."""
    return DraperQFTAdder(num_state_qubits=num_state_qubits)
