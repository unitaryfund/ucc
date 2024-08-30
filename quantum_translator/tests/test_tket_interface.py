from pytket import Circuit
from quantum_translator.tket_interface import TKETInterface
from quantum_translator.qasm_validation import is_valid_openqasm
import pytest

@pytest.mark.skip(reason="Skipping as PyTKET lacks OpenQASM3 conversion as of Aug 21, 2024.")
def test_tket_to_openqasm3():
    # Create a simple TKET circuit
    circuit = Circuit(2)
    circuit.H(0)
    circuit.CX(0, 1)

    # Translate the circuit to OpenQASM3
    qasm_output = TKETInterface.to_qasm(circuit)

    # Validate the output as OpenQASM3
    assert is_valid_openqasm(qasm_output, version='3'), "The generated code is not valid OpenQASM3."

def test_tket_to_openqasm2():
    # Create a simple TKET circuit
    circuit = Circuit(2)
    circuit.H(0)
    circuit.CX(0, 1)

    # Translate the circuit to OpenQASM3
    qasm_output = TKETInterface.to_qasm(circuit)

    # Validate the output as OpenQASM3
    assert is_valid_openqasm(qasm_output, version='2'), "The generated code is not valid OpenQASM3."
