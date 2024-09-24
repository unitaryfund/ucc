import pytest

from pytket import Circuit as TketCircuit
from cirq import Circuit as CirqCircuit
from qiskit import QuantumCircuit as QiskitCircuit
from cirq import H, CNOT, LineQubit

from ucc import compile

def test_qiskit_compile():
    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    result_circuit = compile(circuit, return_format='original')
    assert isinstance(result_circuit, QiskitCircuit)

def test_cirq_compile():
    qubits = LineQubit.range(2)
    circuit = CirqCircuit(H(qubits[0]), CNOT(qubits[0], qubits[1]))
    result_circuit = compile(circuit, return_format='original')
    assert isinstance(result_circuit, CirqCircuit)

def test_tket_compile():
    circuit = TketCircuit(2)
    circuit.H(0)
    circuit.CX(0, 1)
    result_circuit = compile(circuit, return_format='original')
    assert isinstance(result_circuit, TketCircuit)

