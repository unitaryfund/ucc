import importlib
import warnings
from qiskit import transpile as qiskit_transpile
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np

__all__ = [
    "calculate_entanglement_entropy_slope",
    "has_enough_memory",
    "qmprs_available",
    "MPS_Encoder",
    "approx_compile",
]

from .mps_utils import calculate_entanglement_entropy_slope, has_enough_memory

# Check if `qmprs` is installed for AQC compilation
qmprs_available = importlib.util.find_spec("qmprs") is not None
if qmprs_available:
    from .qmprs_compiler import QmprsCompiler as MPS_Encoder
else:
    from .mps_sequential import Sequential as MPS_Encoder


def approx_compile(circuit: QuantumCircuit) -> QuantumCircuit:
    """Compiles the qiskit circuit provided to approximately compile,
    and if the circuit state requires more memory than is available or
    the fidelity of aqc is lower than required it will return the original
    circuit.

    Args:
        qiskit_circuit (QuantumCircuit): The circuit to approximately compile.

    Returns:
        QuantumCircuit: The compiled or unchanged circuit.
    """
    if not qmprs_available:
        warnings.warn(
            "Warning: AQC compilation is requested, but `qmprs` is not installed. "
            "Falling back to vanilla sequential encoding."
        )

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
    aqc_circuit = MPS_Encoder()(target_sv)

    # Fallback protocol for low fidelity, which discards the compiled
    # circuit and returns the original one
    # TODO: This should be modified depending on maintainer notes
    fidelity = np.vdot(target_sv, Statevector(aqc_circuit).data)
    if np.abs(fidelity) < 0.8:
        warnings.warn(
            f"Warning: Fidelity {np.abs(fidelity):.4f} is too low. Discarding compression."
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
