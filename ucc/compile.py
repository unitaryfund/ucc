from qiskit.providers import BackendV2
from qiskit.transpiler import CouplingMap
from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph
from qbraid.transpiler import transpile
from .transpilers.ucc_defaults import UCCDefault1


import sys
import warnings

# Specify the supported Python version range
REQUIRED_MAJOR = 3
MINOR_VERSION_MIN = 12
MINOR_VERSION_MAX = 13

current_major = sys.version_info.major
current_minor = sys.version_info.minor

if current_major != REQUIRED_MAJOR or not (MINOR_VERSION_MIN <= current_minor <= MINOR_VERSION_MAX):
    warnings.warn(
        f"Warning: This package is designed for Python {REQUIRED_MAJOR}.{MINOR_VERSION_MIN}-{REQUIRED_MAJOR}.{MINOR_VERSION_MAX}. "
        f"You are using Python) {current_major}.{current_minor}.")
supported_circuit_formats = ConversionGraph().nodes()


def compile(
    circuit,
    return_format="original",
    target_device=None,
):
    """Compiles the provided quantum `circuit` by translating it to a Qiskit
    circuit, transpiling it, and returning the optimized circuit in the
    specified `return_format`.

    Args:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be returned.
            e.g., "TKET", "OpenQASM2". Check ``ucc.supported_circuit_formats()``.
            Defaults to the format of the input circuit.

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    # Translate to Qiskit Circuit object
    qiskit_circuit = transpile(circuit, "qiskit")
    compiled_circuit = UCCDefault1().run(
        qiskit_circuit,
        coupling_list=get_backend_connectivity(target_device),
    )

    # Translate the compiled circuit to the desired format
    final_result = transpile(compiled_circuit, return_format)
    return final_result


def get_backend_connectivity(target_device = None) -> str:
        """
        Extracts the coupling graph from the provided device in the form of a list of connections between qubits.
        
        Parameters:
            target_device: Can be a Qiskit backend or Qiskit CouplingMap, or a list of connections between qubits. 
                        If None, all-to-all connectivity is assumed.
                        If Qiskit backend or coupling map, only the coupling list extracted from the backend is used.

        Returns:
            coupling_list: The list of connections between qubits.
        """

        if target_device is None:
            coupling_list = None
        elif isinstance(target_device, BackendV2):
            coupling_list = list(target_device.coupling_map.get_edges())
        elif isinstance(target_device, CouplingMap):
            # rustworkx.EdgeList object
            coupling_list = target_device.get_edges()
        elif isinstance(target_device, list):
            # user-specified list of edges of coupling graph
            coupling_list = target_device
        else:
            raise ValueError("Invalid backend type. Must be a Qiskit backend, coupling map, or a list of connections between qubits.")
        
        return coupling_list
