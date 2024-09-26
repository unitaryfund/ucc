import pytest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager

from ..custom_cx import CXCancellation

# Trivial circuit of only CNOTs
num_qubits = 5
cx_only = QuantumCircuit(num_qubits)
for i_layer in range(3):
    for i in range(num_qubits-2):    
        j = (i + 1)
        k = (i + 2)
        cx_only.cx(i, j)
        cx_only.cx(j, k)
        cx_only.cx(i, k)
cx_only_compiled = QuantumCircuit(num_qubits)


def test_cx_cancellation():
    pass_manager = PassManager()
    pass_manager.append(CXCancellation())
    result_circuit = pass_manager.run(cx_only)
    assert result_circuit == cx_only_compiled


#QFT circuit
num_qubits = 8
qft = QuantumCircuit(num_qubits)
for i in range(num_qubits):
    qft.h(i)
    for j in range(i+1, num_qubits):
        qft.cp(np.pi/(2**(j-i)), j, i)

def test_cx_cancellation_qft():
    pass_manager = PassManager()
    pass_manager.append(CXCancellation())
    result_circuit = pass_manager.run(qft)
    # check against result from default Qiskit transpiler
    assert result_circuit.count_ops().get("cx", 0) < 78
