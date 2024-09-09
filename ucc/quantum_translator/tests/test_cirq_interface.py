# tests/test_.interfaces..interfaces.cirq_interface.py

from cirq import Circuit, H, CNOT, LineQubit
from ucc.quantum_translator.interfaces import CirqInterface
from ucc.quantum_translator import QuantumTranslator
import pytest

@pytest.mark.skip(reason="Skipping as cirq lacks OpenQASM3 conversion as of Aug 21, 2024.")
def test_cirq_to_openqasm3():
    # Create a simple Cirq circuit
    qubits = LineQubit.range(2)
    circuit = Circuit(H(qubits[0]), CNOT(qubits[0], qubits[1]))

    # Translate the circuit to OpenQASM3
    qasm_output = CirqInterface.to_qasm(circuit)

    # Validate the output as OpenQASM3
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='3'), "The generated code is not valid OpenQASM3."

def test_cirq_to_openqasm2():
    # Create a simple Cirq circuit
    qubits = LineQubit.range(2)
    circuit = Circuit(H(qubits[0]), CNOT(qubits[0], qubits[1]))

    # Translate the circuit to OpenQASM3
    qasm_output = CirqInterface.to_qasm(circuit)

    # Validate the output as OpenQASM3
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='2'), "The generated code is not valid OpenQASM3."
