# tests/test_qiskit_interface.py

from qiskit import QuantumCircuit
from quantum_translator.qiskit_interface import QiskitInterface
from utils.qasm_validation import is_valid_openqasm

def test_qiskit_to_openqasm3():
    # Create a simple quantum circuit
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    # Translate the circuit to OpenQASM3
    qasm_output = QiskitInterface.translate_to_qasm(circuit)

    # Validate the output as OpenQASM3
    assert is_valid_openqasm(qasm_output, version='3'), "The generated code is not valid OpenQASM3."

