from cirq import Circuit, H, CNOT, LineQubit

def ghz_state(n_qubits):
    qubits = LineQubit.range(n_qubits)
    circuit = Circuit(H(qubits[0]))

    for i in range(n_qubits - 1):
        circuit.append(CNOT(qubits[i], qubits[i+1]))
    
    return circuit
    
