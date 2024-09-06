import pytest
from ucc import compile

from pytket import Circuit as TketCircuit
from cirq import Circuit as CirqCircuit
from qiskit import QuantumCircuit as QiskitCircuit

def test_tket_compile():
    circuit = TketCircuit(2)
    compile(circuit, qasm_version='2', return_format='original')