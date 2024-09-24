from qiskit import QuantumCircuit

def ghz_state(n_qubits):
    circuit = QuantumCircuit(n_qubits)
    circuit.h(0)
    
    for i in range(n_qubits - 1):
        circuit.cx(i, i + 1)
    
    return circuit

