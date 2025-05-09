import pytest
from cirq import Circuit as CirqCircuit
from cirq import CNOT, H, X, LineQubit, NamedQubit
from cirq.testing import assert_same_circuits
from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit
from qiskit.converters import circuit_to_dag
from qiskit.quantum_info import Statevector
from qiskit.transpiler.passes import GatesInBasis
from qiskit.transpiler.passes.utils import CheckMap
from qiskit.transpiler import Target
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.circuit.library import CXGate, HGate, XGate
from ucc import compile
from ucc.transpilers.ucc_defaults import UCCDefault1
import numpy as np


def qcnn_circuit(N, seed=12345):
    """A circuit to generate a Quantum Convolutional Neural Network

    Parameters:
        N (int): Number of qubits

    Returns:
        QiskitCircuit: Output circuit
    """
    rng = np.random.default_rng(seed=seed)

    qc = QiskitCircuit(N)
    num_layers = int(np.ceil(np.log2(N)))
    i_conv = 0
    for i_layer in range(num_layers):
        for i_sub_layer in [0, 2**i_layer]:
            for i_q1 in range(i_sub_layer, N, 2 ** (i_layer + 1)):
                i_q2 = 2**i_layer + i_q1
                if i_q2 < N:
                    qc.rxx(rng.random(), i_q1, i_q2)
                    qc.ry(rng.random(), i_q1)
                    qc.ry(rng.random(), i_q2)
                    i_conv += 1

    return qc


def random_clifford_circuit(num_qubits, seed=12345):
    """Generate a random clifford circuit
    Parameters:
        num_qubits (int): Number of qubits
        seed (int): Optional. Seed the random number generator, default=12345

    Returns:
        QuantumCircuit: Clifford circuit
    """
    # This code is used to generate the QASM file
    from qiskit.circuit.random import random_clifford_circuit

    gates = ["cx", "cz", "cy", "swap", "x", "y", "z", "s", "sdg", "h"]
    qc = random_clifford_circuit(
        num_qubits,
        gates=gates,
        num_gates=10 * num_qubits * num_qubits,
        seed=seed,
    )
    return qc


def test_qiskit_compile():
    circuit = QiskitCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    result_circuit = compile(circuit, return_format="original")
    assert isinstance(result_circuit, QiskitCircuit)


def test_cirq_compile():
    qubits = LineQubit.range(2)
    circuit = CirqCircuit(H(qubits[0]), CNOT(qubits[0], qubits[1]))
    result_circuit = compile(circuit, return_format="original")
    assert isinstance(result_circuit, CirqCircuit)


def test_tket_compile():
    circuit = TketCircuit(2)
    circuit.H(0)
    circuit.CX(0, 1)
    result_circuit = compile(circuit, return_format="original")
    assert isinstance(result_circuit, TketCircuit)


def test_compile_with_target_device():
    circuit = QiskitCircuit(3)
    circuit.cx(0, 1)
    circuit.cx(0, 2)

    # Create a simple target that does not have direct CX between 0 and 2
    t = Target(description="Fake device", num_qubits=3)
    t.add_instruction(CXGate(), {(0, 1): None, (1, 2): None})
    result_circuit = compile(
        circuit, return_format="original", target_device=t
    )

    # Check compilation respected the target device topology
    dag = circuit_to_dag(result_circuit)
    analysis_pass = CheckMap(
        t.build_coupling_map(), property_set_field="check_map"
    )
    analysis_pass.run(dag)
    assert analysis_pass.property_set["check_map"]


def test_custom_pass():
    """Verify that a custom pass works with a non-qiskit input circuit"""

    class HtoX(TransformationPass):
        """Toy transformation that converts all H gates to X gates"""

        def run(self, dag):
            for node in dag.op_nodes():
                if isinstance(node.op, HGate):
                    dag.substitute_node(node, XGate())
            return dag

    # Example usage with a cirq circuit, stil showcasing the cross-frontend compatibility

    qubit = NamedQubit("q_0")
    cirq_circuit = CirqCircuit(H(qubit))

    post_compiler_circuit = compile(cirq_circuit, custom_passes=[HtoX()])
    assert_same_circuits(post_compiler_circuit, CirqCircuit(X(qubit)))


@pytest.mark.parametrize(
    "circuit_function", [qcnn_circuit, random_clifford_circuit]
)
@pytest.mark.parametrize("num_qubits", [6, 7, 8, 9, 10])
@pytest.mark.parametrize("seed", [1, 326, 5678, 12345])
def test_compilation_retains_gateset(circuit_function, num_qubits, seed):
    circuit = circuit_function(num_qubits, seed)
    transpiler = UCCDefault1()
    target_basis = transpiler.target_basis
    transpiled_circuit = transpiler.run(circuit)
    dag = circuit_to_dag(transpiled_circuit)
    analysis_pass = GatesInBasis(basis_gates=target_basis)
    analysis_pass.run(dag)
    assert analysis_pass.property_set["all_gates_in_basis"]


# Test compilation accepts QASM circuits containing IF-ELSE
def test_compile_if_else():
    qasm = """
    OPENQASM 3;
    include "stdgates.inc";
    bit[3] data;
    bit[2] syndrome;
    qubit[3] q0;
    qubit[2] q1;

    syndrome[0] = measure q0[0];
    syndrome[1] = measure q1[1];
    if (syndrome[0]) {
        x q1[0];
    }
    if (syndrome[1]) {
        x q1[0];
    }
    """
    transpiled = compile(qasm, return_format="qiskit")
    assert isinstance(transpiled, QiskitCircuit)


@pytest.mark.parametrize(
    "circuit_function", [qcnn_circuit, random_clifford_circuit]
)
@pytest.mark.parametrize("num_qubits", [6, 7, 8, 9, 10, 15])
@pytest.mark.parametrize("seed", [1, 326, 5678, 12345])
def test_compiled_circuits_equivalent(circuit_function, num_qubits, seed):
    circuit = circuit_function(num_qubits, seed)
    transpiled = compile(circuit, return_format="qiskit")
    sv1 = Statevector(circuit)
    sv2 = Statevector(transpiled)
    assert sv1.equiv(sv2)
