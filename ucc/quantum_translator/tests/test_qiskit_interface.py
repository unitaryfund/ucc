# tests/test_.interfaces.qiskit_interface.py

from qiskit import QuantumCircuit
from ucc.quantum_translator.interfaces import QiskitInterface
from ucc.quantum_translator import QuantumTranslator

# Create a simple quantum circuit
circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)

def test_qiskit_to_openqasm3():
    # Translate the circuit to OpenQASM3
    qasm_output = QiskitInterface.to_qasm(circuit, version='3')
    print(qasm_output)
    # Validate the output as OpenQASM3
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='3'), "The generated code is not valid OpenQASM3."

def test_qiskit_to_openqasm2():
    # Translate the circuit to OpenQASM2
    qasm_output = QiskitInterface.to_qasm(circuit, version='2')

    # Validate the output as OpenQASM3
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='2'), "The generated code is not valid OpenQASM2."
