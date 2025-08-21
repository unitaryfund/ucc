from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph
from qbraid.transpiler import transpile as translate
from qiskit import transpile as qiskit_transpile
from .transpilers.ucc_defaults import UCCDefault1

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
            e.g. {"cx", "rx",...}. Defaults to the gate set of the target device if available. If no `target_gateset` or ` target_device` is provided, defaults to `{"cx", "rz", "rx", "ry", "h"}`.
        target_device (qiskit.transpiler.Target): (optional)
            The target device  to compile the circuit for. Can be specified as a Qiskit backend. If None, all-to-all connectivity is assumed. If a `target_device` is specified, `target_device.operation_names` supercedes the `target_gateset`.
        custom_passes (list[qiskit.transpiler.TransformationPass]): (optional)
            A list of custom passes to apply after the default set
            of passes. Defaults to None.

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    # Translate to Qiskit Circuit object
    qiskit_circuit = translate(circuit, "qiskit")

    # Initialize the UCCDefault1 compiler with the target device and gateset
    ucc_default1 = UCCDefault1(
        target_device=target_device, target_gateset=target_gateset
    )

    # Translate into the target device gateset first; no optimization
    basis_translated_circuit = qiskit_transpile(
        qiskit_circuit,
        basis_gates=ucc_default1.target_gateset,
        optimization_level=0,
    )

    if custom_passes is not None:
        ucc_default1.pass_manager.append(custom_passes)

    # Compile the circuit using the UCCDefault1 pass manager
    compiled_circuit = ucc_default1.run(basis_translated_circuit)

    # Translate the compiled circuit to the desired format
    final_result = translate(compiled_circuit, return_format)
    return final_result
