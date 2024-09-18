from qiskit import transpile, QuantumCircuit
from ..quantum_translator import QuantumTranslator

from ucc.transpilers.ucc_defaults import UCCDefault1


class UCCTranspiler:
    @staticmethod
    def transpile(qasm_code: str, mode: str = 'qiskit', draw = False, get_gate_counts = False) -> str:
        """
        transpiles the given QASM code using Qiskit's transpile function.
        mode = 'qiskit' just translates QASM to Qiskit, running qiskit.transpile with the maximum optimization level,
        then translates back to QASM for testing purposes. 
        TODO: create a DAG object from the qasm_code directly and only call subset of
        Qiskit compiler passes.

        mode = 'ucc' uses the UCCDefault1 transpiler from UCC to transpile the QASM code.
        
        Parameters:
            qasm_code (str): The OpenQASM code to transpile.
            mode (str): The transpiler to use. 'qiskit' or 'ucc'.
            draw (bool): Whether to draw the transpiled circuit.
            get_gate_counts (bool): Whether to return the gate counts of the transpiled circuit.

        Returns:
            QuantumCircuit: The transpiled quantum circuit.
        """
        # Parse the QASM code into a Qiskit QuantumCircuit
        circuit = QuantumCircuit.from_qasm_str(qasm_code)
        
        # Transpile (transpile) the circuit
        if mode == 'qiskit':
            transpiled_circuit = transpile(circuit, optimization_level=3)
        elif mode == 'ucc':
            ucc_transpiler = UCCDefault1()
            transpiled_circuit = ucc_transpiler.run(circuit)

        if draw:
            print(transpiled_circuit)

        if get_gate_counts:
            gate_counts = transpiled_circuit.count_ops()
        else:
            gate_counts = None
        
        transpiled_qasm = QuantumTranslator.to_qasm(circuit=transpiled_circuit)

        return transpiled_qasm, gate_counts

