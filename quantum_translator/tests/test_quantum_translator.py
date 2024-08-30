import pytest
from quantum_translator import QuantumTranslator
from pytket import Circuit as TketCircuit
from cirq import Circuit as CirqCircuit
from qiskit import QuantumCircuit as QiskitCircuit

# Test for supported types
def test_supported_types():
    expected = "pytket.Circuit, cirq.Circuit, qiskit.QuantumCircuit, OpenQASM2"
    assert QuantumTranslator.supported_types() == expected

# Test valid TKET circuit to OpenQASM2 translation
def test_tket_to_qasm2():
    circuit = TketCircuit(2)
    qasm_output = QuantumTranslator.to_qasm(circuit, version='2')
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='2')

# Test valid Qiskit circuit to OpenQASM2 translation
def test_qiskit_to_qasm2():
    circuit = QiskitCircuit(2)
    qasm_output = QuantumTranslator.to_qasm(circuit, version='2')
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='2')

# Test valid Cirq circuit to OpenQASM2 translation
def test_cirq_to_qasm2():
    circuit = CirqCircuit()
    qasm_output = QuantumTranslator.to_qasm(circuit, version='2')
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='2')

# Test valid OpenQASM2 input
def test_valid_openqasm2_input():
    openqasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    h q[0];
    cx q[0], q[1];
    """
    assert QuantumTranslator.is_valid_openqasm(openqasm_str, version='2')

# Test valid OpenQASM3 input
def test_valid_openqasm3_input():
    openqasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q[0];
    cx q[0], q[1];
    """
    assert QuantumTranslator.is_valid_openqasm(openqasm_str, version='3')

# Test invalid circuit type
def test_invalid_circuit_type():
    class CustomCircuit:
        pass
    
    with pytest.raises(TypeError):
        QuantumTranslator.to_qasm(CustomCircuit())

# Test invalid OpenQASM2 string
def test_invalid_openqasm2_string():
    invalid_qasm = "INVALID OPENQASM CODE"
    assert not QuantumTranslator.is_valid_openqasm(invalid_qasm, version='2')

# Test invalid OpenQASM3 string
def test_invalid_openqasm3_string():
    invalid_qasm = "INVALID OPENQASM CODE"
    assert not QuantumTranslator.is_valid_openqasm(invalid_qasm, version='3')

# Test OpenQASM3 translation from a Qiskit circuit
def test_qiskit_to_qasm3():
    circuit = QiskitCircuit(2)
    qasm_output = QuantumTranslator.to_qasm(circuit, version='3')
    assert QuantumTranslator.is_valid_openqasm(qasm_output, version='3')
