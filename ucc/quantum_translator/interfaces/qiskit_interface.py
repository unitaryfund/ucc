from qiskit import QuantumCircuit, qasm3, qasm2

class QiskitInterface:
    @staticmethod
    def to_qasm(circuit: QuantumCircuit, version='2') -> str:
        """Translates a Qiskit circuit to OpenQASM string of the version specified."""
        if version == '2':
            return qasm2.dumps(circuit)
        elif version =='3':
            return qasm3.dumps(circuit)    
