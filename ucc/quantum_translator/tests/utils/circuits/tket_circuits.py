from pytket import Circuit

def ghz_state(n_qubits):
    circuit = Circuit(n_qubits)
    circuit.H(0)
    
    for i in range(n_qubits - 1):
        circuit.CX(i, i + 1)
    
    return circuit

