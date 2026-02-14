from qiskit import QuantumCircuit
from qiskit import transpile as qiskit_transpile
from qiskit.quantum_info import Statevector, Operator
import numpy as np
import warnings

__all__ = [
    "StateSweepApproximator",
    "UnitarySweepApproximator",
    "generate_staircase_ansatz",
    "generate_brickwall_ansatz",
    "approx_state_compile",
    "approx_unitary_compile",
    "StateSweepPass",
    "UnitarySweepPass",
]

from ..utils import has_enough_memory
from .approx_state import StateSweepApproximator
from .approx_unitary import UnitarySweepApproximator, hst_fidelity
from .ansatzes import (
    generate_staircase_ansatz,
    generate_brickwall_ansatz,
)
from .sweep_pass import StateSweepPass, UnitarySweepPass


def approx_state_compile(circuit: QuantumCircuit) -> QuantumCircuit:
    """Compiles the qiskit circuit provided to approximately compile,
    and if the circuit state requires more memory than is available or
    the fidelity of aqc is lower than required it will return the original
    circuit.

    Args:
        qiskit_circuit (QuantumCircuit): The circuit to approximately compile.

    Returns:
        QuantumCircuit: The compiled or unchanged circuit.
    """
    if circuit.num_qubits == 1:
        return circuit

    # If the circuit's statevector IR requires more RAM than the user has,
    # ignore the compilation and return the inputted circuit as is
    has_memory, required_memory, available_memory = has_enough_memory(
        circuit.num_qubits
    )
    if not has_memory:
        warnings.warn(
            "Required memory to store statevector IR is more than available memory. \n"
            f"Required_memory: {required_memory} GB \n"
            f"Available memory to allocate to storing statevector IR: {available_memory} GB \n\n"
        )
        return circuit

    target_sv = Statevector(circuit).data
    aqc_circuit = StateSweepApproximator()(
        target_sv,
        unitary_layers=generate_staircase_ansatz(
            circuit.num_qubits, num_layers=max(1, circuit.num_qubits // 2)
        ),
        num_sweeps=50 * circuit.num_qubits,
    )

    # Fallback protocol for low fidelity, which discards the compiled
    # circuit and returns the original one
    # TODO: This should be modified depending on maintainer notes
    fidelity = np.abs(np.vdot(target_sv, Statevector(aqc_circuit).data)) ** 2
    if fidelity < 0.8:
        warnings.warn(
            f"Warning: Fidelity {fidelity:.4f} is too low. Discarding compression."
        )
        return circuit

    # If the compiled circuit is deeper and has more cx than permitted, discard
    # the compilation
    aqc_transpiled = qiskit_transpile(
        aqc_circuit, basis_gates=["u3", "cx"], optimization_level=3
    )
    original_transpiled = qiskit_transpile(
        circuit, basis_gates=["u3", "cx"], optimization_level=3
    )

    aqc_cx_count = aqc_transpiled.count_ops().get("cx", 0)
    aqc_depth = aqc_transpiled.depth()

    original_cx_count = original_transpiled.count_ops().get("cx", 0)
    original_depth = original_transpiled.depth()

    # Fallback protocol for worse depth and cx counts, which discards
    # the compiled circuit and returns the original one
    # TODO: This should be modified depending on maintainer notes
    if (aqc_cx_count >= original_cx_count) and (aqc_depth >= original_depth):
        return circuit

    return aqc_circuit


def approx_unitary_compile(circuit: QuantumCircuit) -> QuantumCircuit:
    """Compiles the qiskit circuit provided to approximately compile,
    and if the circuit state requires more memory than is available or
    the fidelity of aqc is lower than required it will return the original
    circuit.

    Args:
        qiskit_circuit (QuantumCircuit): The circuit to approximately compile.

    Returns:
        QuantumCircuit: The compiled or unchanged circuit.
    """
    if circuit.num_qubits == 1:
        return circuit

    # If the circuit's statevector IR requires more RAM than the user has,
    # ignore the compilation and return the inputted circuit as is
    has_memory, required_memory, available_memory = has_enough_memory(
        circuit.num_qubits
    )
    if not has_memory:
        warnings.warn(
            "Required memory to store statevector IR is more than available memory. \n"
            f"Required_memory: {required_memory} GB \n"
            f"Available memory to allocate to storing statevector IR: {available_memory} GB \n\n"
        )
        return circuit

    target_unitary = Operator(circuit).data
    aqc_circuit = UnitarySweepApproximator()(
        target_unitary,
        unitary_layers=generate_staircase_ansatz(
            circuit.num_qubits,
            num_layers=int(np.ceil(circuit.num_qubits * 1.5)),
        ),
        num_sweeps=50 * circuit.num_qubits,
    )

    # Fallback protocol for low fidelity, which discards the compiled
    # circuit and returns the original one
    fidelity = hst_fidelity(
        target_unitary, Operator(aqc_circuit).data, circuit.num_qubits
    )

    if fidelity < 0.8:
        warnings.warn(
            f"Warning: Fidelity {fidelity:.4f} is too low. Discarding compression."
        )
        return circuit

    # If the compiled circuit is deeper and has more cx than permitted, discard
    # the compilation
    aqc_transpiled = qiskit_transpile(
        aqc_circuit, basis_gates=["u3", "cx"], optimization_level=3
    )
    original_transpiled = qiskit_transpile(
        circuit, basis_gates=["u3", "cx"], optimization_level=3
    )

    aqc_cx_count = aqc_transpiled.count_ops().get("cx", 0)
    aqc_depth = aqc_transpiled.depth()

    original_cx_count = original_transpiled.count_ops().get("cx", 0)
    original_depth = original_transpiled.depth()

    # Fallback protocol for worse depth and cx counts, which discards
    # the compiled circuit and returns the original one
    # TODO: This should be modified depending on maintainer notes
    if (aqc_cx_count >= original_cx_count) and (aqc_depth >= original_depth):
        return circuit

    return aqc_circuit
