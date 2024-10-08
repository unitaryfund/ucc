import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel

from ..basis_translator import BasisTranslator
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
cx_only_compiled.cx(2, 4)


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
    target_basis = ['rz', 'rx', 'ry', 'h', 'cx']
    pass_manager.append(BasisTranslator(sel, target_basis))
    pass_manager.append(CXCancellation())
    result_circuit = pass_manager.run(qft)
    # check against result from default Qiskit transpiler
    assert 0 < result_circuit.count_ops().get("cx", 0) < 78


num_qubits = 2
rz_angle = 0.9823754  # random angle
CX_RZ_CX_circuit = QuantumCircuit(num_qubits)
CX_RZ_CX_circuit.cx(0, 1)
CX_RZ_CX_circuit.rz(rz_angle, 0)
CX_RZ_CX_circuit.cx(0, 1)

CX_RZ_CX_circuit_ideal_compiled = QuantumCircuit(num_qubits)
CX_RZ_CX_circuit_ideal_compiled.rz(rz_angle, 0)


def test_commutation_rule_used():
    pass_manager = PassManager()
    target_basis = ['rz', 'rx', 'ry', 'h', 'cx']
    pass_manager.append(BasisTranslator(sel, target_basis))
    pass_manager.append(CXCancellation())
    compiled_circuit = pass_manager.run(CX_RZ_CX_circuit)
    assert compiled_circuit == CX_RZ_CX_circuit_ideal_compiled
