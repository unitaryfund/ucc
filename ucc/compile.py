from ucc.quantum_translator import QuantumTranslator
from ucc.transpilers import UCCTranspiler
from qbraid.transpiler import transpile
from qbraid.programs.alias_manager import get_program_type_alias


def compile(circuit, return_format='original', mode='ucc', get_gate_counts=False):
    """
    Compiles provided quantum `circuit` by translating it to a Qiskit circuit, transpiling using the specified transpiler `mode`, and returning the optimized circuit in specified `return_format`.

    Parameters:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be 
            returned. e.g. "TKET", "OpenQASM2" 
            Check `ucc.QuantumTranslator.supported_circuit_formats()`
            Defaults to format of input circuit. 
            mode (str): 'ucc' or 'qiskit, specifies transpiler mode to use
    
    Returns:
        variable type: Compiled circuit 
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)
    
    qiskit_circuit = transpile(circuit, "qiskit") 
    compiled_circuit, gate_counts = UCCTranspiler.transpile(qiskit_circuit, mode=mode,  get_gate_counts=get_gate_counts)

    final_result = transpile(compiled_circuit, return_format)
    if get_gate_counts:
        return final_result, gate_counts
    else:
        return final_result
