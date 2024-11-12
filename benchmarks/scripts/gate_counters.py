def count_multi_qubit_gates_pytket(pytket_circuit):
    """
    Counts the number of multi-qubit operations in a given PyTkets circuit.

    Args:
        circuit (Circuit): The input PyTkets circuit.

    Returns:
        int: The number of multi-qubit gates in the circuit.
    """
    multi_qubit_gate_count = pytket_circuit.n_gates - pytket_circuit.n_1qb_gates()

    return multi_qubit_gate_count


def count_multi_qubit_gates_qiskit(qiskit_circuit):
    """
    Counts the number of multi-qubit operations in the given circuit without decomposing.

    Args:
        circuit (QuantumCircuit): The input quantum circuit.

    Returns:
        int: The number of multi-qubit gates in the circuit.
    """
    multi_qubit_gate_count = 0
    
    # Iterate over each instruction in the circuit
    for instruction, _, _ in qiskit_circuit.data:
        if instruction.num_qubits > 1:
            multi_qubit_gate_count += 1

    return multi_qubit_gate_count


def count_multi_qubit_gates_cirq(cirq_circuit):
    """
    Counts the number of multi-qubit operations in a given Cirq circuit.

    Args:
        circuit (cirq.Circuit): The input Cirq circuit.

    Returns:
        int: The number of multi-qubit gates in the circuit.
    """
    multi_qubit_gate_count = 0
    
    # Iterate over each operation in the circuit
    for operation in cirq_circuit.all_operations():
        if len(operation.qubits) > 1:  # Check if the operation acts on more than one qubit
            multi_qubit_gate_count += 1

    return multi_qubit_gate_count

