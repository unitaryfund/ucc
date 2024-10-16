from random import seed
import pytest

from ucc import compile
from benchmarks.circuits import qcnn_circuit, random_clifford_circuit

from qiskit.quantum_info import Statevector



benchmark_circuits = [
    "qcnn_circuit",
    "random_clifford_circuit",
]


@pytest.mark.parametrize("benchmark_circuit", benchmark_circuits)
@pytest.mark.parametrize("num_qubits", [4, 5, 6, 7, 8, 9, 10])
@pytest.mark.parametrize("seed", [1, 326, 5678, 12345])
def test_compiled_circuits_equivalent(benchmark_circuit, num_qubits, seed):
    if benchmark_circuit == "qcnn_circuit":
       circuit = qcnn_circuit(num_qubits)
    elif benchmark_circuit == "random_clifford_circuit":
        circuit = random_clifford_circuit(num_qubits, seed)
    transpiled = compile(circuit, return_format='qiskit')
    sv1 = Statevector(circuit)
    sv2 = Statevector(transpiled)
    assert sv1.equiv(sv2)
