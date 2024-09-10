from ucc.quantum_translator import QuantumTranslator
from ucc.transpilers import UCCTranspiler

def compile(circuit, qasm_version='2', return_format='original', mode='qiskit', draw=False, get_gate_counts=False):
    """
    Processes the provided quantum circuit using the QuantumTranslator 
    and compiles it using the Compiler. Why is it called a compiler and not
     a transpiler? To keep things general, even though it's currently just 
     transpiling.

    Parameters:
        circuit (object): The quantum circuit to be compiled.
        qasm_version (str): OpenQASM version ('2' or '3').
        return_format (str): The format in which your circuit will be 
            returned. e.g. "TKET", "OpenQASM2" 
            Check `ucc.QuantumTranslator.supported_circuit_formats()`
            Defaults to format of input circuit. 
    
    Returns:
        variable type : Compiled circuit result 
    """
    translator = QuantumTranslator(circuit, return_format)
    qasm_code = translator.to_qasm(circuit, version=qasm_version)

    compiled_qasm, gate_counts = UCCTranspiler.transpile(qasm_code, mode=mode, draw=draw, get_gate_counts=get_gate_counts)
    # print(compiled_qasm)
    final_result = translator.to_return_format(compiled_qasm)

    if get_gate_counts:
        return final_result, gate_counts
    else:
        return final_result
