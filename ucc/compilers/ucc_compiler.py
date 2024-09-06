from qiskit import transpile, QuantumCircuit

class UCCCompiler:
    @staticmethod
    def transpile(qasm_code: str):
        """
        transpiles the given QASM code using Qiskit's transpile function.
        
        Parameters:
            qasm_code (str): The OpenQASM code to transpile.

        Returns:
            QuantumCircuit: The transpiled quantum circuit.
        """
        # Parse the QASM code into a Qiskit QuantumCircuit
        circuit = QuantumCircuit.from_qasm_str(qasm_code)
        
        # Transpile (transpile) the circuit
        transpiled_circuit = transpile(circuit)
        
        return transpiled_circuit
