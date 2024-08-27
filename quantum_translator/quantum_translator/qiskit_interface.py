from qiskit import QuantumCircuit, qasm3

class QiskitInterface:
    @staticmethod
    def translate_to_qasm(circuit: QuantumCircuit) -> str:
        """Translates a Qiskit circuit to OpenQASM3 string."""
        return qasm3.dumps(circuit)
