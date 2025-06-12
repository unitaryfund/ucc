from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph
from qbraid.transpiler import transpile as translate
from .transpilers.ucc_defaults import UCCDefault1
from qiskit import transpile as qiskit_transpile

import sys
import warnings

# Specify the supported Python version range
REQUIRED_MAJOR = 3
MINOR_VERSION_MIN = 12
MINOR_VERSION_MAX = 13

current_major = sys.version_info.major
current_minor = sys.version_info.minor

if current_major != REQUIRED_MAJOR or not (
    MINOR_VERSION_MIN <= current_minor <= MINOR_VERSION_MAX
):
    warnings.warn(
        f"Warning: This package is designed for Python {REQUIRED_MAJOR}.{MINOR_VERSION_MIN}-{REQUIRED_MAJOR}.{MINOR_VERSION_MAX}. "
        f"You are using Python) {current_major}.{current_minor}."
    )
supported_circuit_formats = ConversionGraph().nodes()


def compile(
    circuit,
    return_format="original",
    target_gateset=None,
    target_device=None,
    custom_passes=None,
):
    """Compiles the provided quantum `circuit` by translating it to a Qiskit
    circuit, transpiling it, and returning the optimized circuit in the
    specified `return_format`.

    Args:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be returned.
            e.g., "TKET", "OpenQASM2". Check ``ucc.supported_circuit_formats``.
            Defaults to the format of the input circuit.
        target_gateset (set[str]): (optional) The gateset to compile the circuit to.
            e.g. {"cx", "rx",...}. Defaults to the gate set of the target device if
            available. If no `target_gateset` or ` target_device` is provided, the
            basis gates of the input circuit are not changed.
        target_device (qiskit.transpiler.Target): (optional) The target device to compile the circuit for. None if no device to target
        custom_passes (list[qiskit.transpiler.TransformationPass]): (optional) A list of custom passes to apply after the default set
            of passes. Defaults to None.

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    # Translate to Qiskit Circuit object
    qiskit_circuit = translate(circuit, "qiskit")

    ucc_default1 = UCCDefault1(target_device=target_device)
    if custom_passes is not None:
        ucc_default1.pass_manager.append(custom_passes)
    compiled_circuit = ucc_default1.run(qiskit_circuit)

    if target_gateset is not None:
        # Translate into user-defined gateset; no optimization
        compiled_circuit = qiskit_transpile(
            compiled_circuit, basis_gates=target_gateset, optimization_level=0
        )
    elif hasattr(target_device, "operation_names"):
        if target_gateset not in target_device.operation_names:
            warnings.warn(
                f"Warning: The target gateset {target_gateset} is not supported by the target device. "
            )
        # Use target_device gateset if available
        target_gateset = target_device.operation_names

        # Translate into the target device gateset; no optimization
        compiled_circuit = qiskit_transpile(
            compiled_circuit,
            basis_gates=target_gateset,
            optimization_level=0,
        )

    # Translate the compiled circuit to the desired format
    final_result = translate(compiled_circuit, return_format)
    return final_result
