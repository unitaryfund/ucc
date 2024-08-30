from quantum_translator.openqasm_interface import OpenQASMInterface
from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit
from cirq import Circuit as CirqCircuit

openqasm_str = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    h q[0];
    cx q[0], q[1];
    """
# Test for translating OpenQASM2 to TKET
def test_translate_to_tket():
    tket_circuit = OpenQASMInterface.to_tket(openqasm_str)
    assert isinstance(tket_circuit, TketCircuit), "Translation to TKET failed."

# Test for translating OpenQASM2 to Cirq
def test_translate_to_cirq():
    cirq_circuit = OpenQASMInterface.to_cirq(openqasm_str)
    assert isinstance(cirq_circuit, CirqCircuit), "Translation to Cirq failed."

# Test for translating OpenQASM2/3 to Qiskit
def test_translate_to_qiskit():
    qiskit_circuit = OpenQASMInterface.to_qiskit(openqasm_str)
    assert isinstance(qiskit_circuit, QiskitCircuit), "Translation to Qiskit failed."
