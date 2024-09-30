import pytest

from ucc import compile
from benchmarks.circuits import qcnn_circuit, random_clifford_circuit, bv_all_ones

from qiskit.quantum_info import Statevector


num_qubits = 4
circuits = [
    qcnn_circuit(num_qubits),
    random_clifford_circuit(num_qubits),
    # bv_all_ones(num_qubits), # BUG: this circuit currently fails
]


@pytest.mark.parametrize("circuit", circuits)
def test_compiled_circuits_equivalent(circuit):
    transpiled = compile(circuit)
    sv1 = Statevector(circuit)
    sv2 = Statevector(transpiled)
    assert sv1.equiv(sv2)
