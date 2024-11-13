from ucc.transpilers import UCCTranspiler
from qbraid.transpiler import transpile
from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph

supported_circuit_formats = ConversionGraph().nodes()


def compile(
    circuit,
    return_format="original",
    mode="ucc",
    target_device=None,
    get_gate_counts=False,
):
    """Compiles the provided quantum `circuit` by translating it to a Qiskit circuit,
    transpiling using the specified `mode`, and returning the optimized circuit in
    the specified `return_format`.

    Args:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be returned.
            e.g., "TKET", "OpenQASM2". Check ``ucc.supported_circuit_formats()``.
            Defaults to the format of the input circuit.
        mode (str): Specifies the transpiler mode to use, either 'ucc' or 'qiskit'.

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    # Currently all circuits are translated to Qiskit Circuit objects before DAG optimization
    qiskit_circuit = transpile(circuit, "qiskit")
    compiled_circuit, gate_counts = UCCTranspiler.transpile(
        qiskit_circuit,
        mode=mode,
        get_gate_counts=get_gate_counts,
        target_device=target_device,
    )

    final_result = transpile(compiled_circuit, return_format)
    if get_gate_counts:
        return final_result, gate_counts
    else:
        return final_result
