from qiskit import transpile, QuantumCircuit
from ..quantum_translator import QuantumTranslator
class UCCTranspiler:
    @staticmethod
    def transpile(qasm_code: str):
        """
        transpiles the given QASM code using Qiskit's transpile function.
        Currently this is just translating QASM to Qiskit, running qiskit.transpile, 
        then translating back to QASM for testing purposes. 
        TODO: create a DAG object from the qasm_code directly and only call subset of Qiskit compiler passes.
        
        Parameters:
            qasm_code (str): The OpenQASM code to transpile.

        Returns:
            QuantumCircuit: The transpiled quantum circuit.
        """
        # Parse the QASM code into a Qiskit QuantumCircuit
        circuit = QuantumCircuit.from_qasm_str(qasm_code)
        
        # Transpile (transpile) the circuit
        transpiled_circuit = transpile(circuit)
        transpiled_qasm = QuantumTranslator.to_qasm(circuit=transpiled_circuit)

        return transpiled_qasm
