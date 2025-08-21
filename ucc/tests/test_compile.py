import pytest
from cirq import Circuit as CirqCircuit
from cirq import CNOT, H, X, LineQubit, NamedQubit
from cirq.testing import assert_same_circuits
from pytket import Circuit as TketCircuit
from qiskit import QuantumCircuit as QiskitCircuit
from qiskit import transpile as qiskit_transpile
from qiskit.converters import circuit_to_dag
from qiskit.quantum_info import Statevector
from qiskit.transpiler.passes import GatesInBasis, CountOps
from qiskit.transpiler.passes.utils import CheckMap
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.circuit.library import HGate, XGate
from ucc.tests.mock_backends import Mybackend
from ucc import compile
from ucc.transpilers.ucc_defaults import UCCDefault1
from ucc.transpilers.aqc.mps_pass import MPSPass
import numpy as np


def random_area_law_circuit(N, seed=12345):
    """A circuit to generate a random area-law statevector.

    Parameters:
        N (int): Number of qubits

    Returns:
        QiskitCircuit: Output circuit
    """
    np.random.seed(seed)

    state = np.random.rand(2**N) + 1j * np.random.rand(2**N)
    state /= np.linalg.norm(state)

    circuit = QiskitCircuit(N)
    circuit.initialize(state, range(N))

    return circuit


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

    def test_compile_target_device_opset():
        circuit = QiskitCircuit(3)
        circuit.cx(0, 1)
        circuit.cx(0, 2)

        # Create a simple target that does not have direct CX between 0 and 2
        t = Mybackend().target
        result_circuit = compile(
            circuit, return_format="original", target_device=t
        )
        # Check that the gates in the final circuit are all supported on the target device
        assert set(op.name for op in result_circuit).issubset(
            t.operation_names
        )

    def test_compile_target_device_coupling_map():
        circuit = QiskitCircuit(3)
        circuit.cx(0, 1)
        circuit.cx(0, 2)

        # Create a simple target that does not have direct CX between 0 and 2
        t = Mybackend().target
        result_circuit = compile(
            circuit, return_format="original", target_device=t
        )
        # Check that the compiled circuit respects the coupling map of the target device
        analysis_pass = CheckMap(
            t.build_coupling_map(), property_set_field="check_map"
        )

        dag = circuit_to_dag(result_circuit)
        analysis_pass.run(dag)
        assert analysis_pass.property_set["check_map"]


def test_compile_with_no_target_gateset_or_device():
    """Test that the final circuit is in the default gateset if no `target_gateset` or `target_device` is provided."""
    circuit = QiskitCircuit(2)
    circuit.cx(0, 1)
    circuit.h(0)

    result_circuit = compile(
        circuit,
    )

    assert set(op.name for op in result_circuit).issubset(
        {"cx", "rz", "rx", "ry", "h"}
    )


def test_bqskit_compile():
    from ucc.transpilers.ucc_bqskit import BQSKitTransformationPass

    bqskit_pass = BQSKitTransformationPass()
    qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[3];
        h q[0];
        cp(1.5707963267948966) q[1], q[0];
        h q[1];
        cp(0.7853981633974483) q[2], q[0];
        cp(1.5707963267948966) q[2], q[1];
        h q[2];
        swap q[0], q[2];
        h q[0];
        cp(-1.5707963267948966) q[1], q[0];
        h q[1];
        cp(-0.7853981633974483) q[2], q[0];
        cp(-1.5707963267948966) q[2], q[1];
        h q[2];
        swap q[0], q[2];
        """
    # This qasm describes a 3-qubit QFT followed by a 3-qubit inverse QFT.
    # This circuit resolves to the identity, but that's not obvious to
    # most synthesis tools.
    # BQSKit using LEAP will usually remove all 2-qubit gates
    # from the circuit, leaving 3 u3 gates that don't do anything
    # because it just focuses on the 2-qubit gates. A further
    # post processing step would remove these 1-qubit gates, but in
    # more realistic use cases, its often not worth the extra processing.

    def get_post_cx_count(circuit, custom_passes=[]):
        post_compiler_circuit = compile(qasm, custom_passes=custom_passes)
        analysis_pass = CountOps()
        dag = circuit_to_dag(
            QiskitCircuit.from_qasm_str(post_compiler_circuit)
        )
        analysis_pass.run(dag)
        if "cx" in analysis_pass.property_set["count_ops"]:
            return analysis_pass.property_set["count_ops"]["cx"]
        else:
            return 0

    assert get_post_cx_count(qasm, [bqskit_pass]) < get_post_cx_count(qasm)


@pytest.mark.parametrize("N", [5, 8, 10, 11])
def test_compile_with_mps_pass(N):
    """Test that the circuit compiled by `MPSPass` works as expected."""
    circuit = random_area_law_circuit(N)
    circuit = qiskit_transpile(circuit, basis_gates=["u3", "cx"])

    compiled_circuit = compile(
        circuit, target_gateset=["u3", "cx"], custom_passes=[MPSPass()]
    )

    # Check that the fidelity is above 0.9
    fidelity = np.vdot(
        Statevector(circuit).data, Statevector(compiled_circuit).data
    )

    assert np.abs(fidelity) > 0.9

    # Assert circuit depth and number of cx gates is lower
    assert circuit.depth() > compiled_circuit.depth()
    assert circuit.count_ops().get("cx", 0) > compiled_circuit.count_ops().get(
        "cx", 0
    )


def test_compile_trivial_state_with_mps_pass():
    """Test that `MPSPass` does not use CX gates when state has no entanglement."""
    qasm = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[10];
        ry(pi/2) q[9];
        rx(pi) q[9];
        rz(pi/4) q[9];
        cx q[9],q[8];
        rz(-pi/4) q[8];
        cx q[9],q[8];
        rz(pi/4) q[8];
        ry(pi/2) q[8];
        rx(pi) q[8];
        rz(pi/4) q[8];
        rz(pi/8) q[9];
        cx q[9],q[7];
        rz(-pi/8) q[7];
        cx q[9],q[7];
        rz(pi/8) q[7];
        cx q[8],q[7];
        rz(-pi/4) q[7];
        cx q[8],q[7];
        rz(pi/4) q[7];
        ry(pi/2) q[7];
        rx(pi) q[7];
        rz(pi/4) q[7];
        rz(pi/8) q[8];
        rz(pi/16) q[9];
        cx q[9],q[6];
        rz(-pi/16) q[6];
        cx q[9],q[6];
        rz(pi/16) q[6];
        cx q[8],q[6];
        rz(-pi/8) q[6];
        cx q[8],q[6];
        rz(pi/8) q[6];
        cx q[7],q[6];
        rz(-pi/4) q[6];
        cx q[7],q[6];
        rz(pi/4) q[6];
        ry(pi/2) q[6];
        rx(pi) q[6];
        rz(pi/4) q[6];
        rz(pi/8) q[7];
        rz(pi/16) q[8];
        rz(pi/32) q[9];
        cx q[9],q[5];
        rz(-pi/32) q[5];
        cx q[9],q[5];
        rz(pi/32) q[5];
        cx q[8],q[5];
        rz(-pi/16) q[5];
        cx q[8],q[5];
        rz(pi/16) q[5];
        cx q[7],q[5];
        rz(-pi/8) q[5];
        cx q[7],q[5];
        rz(pi/8) q[5];
        cx q[6],q[5];
        rz(-pi/4) q[5];
        cx q[6],q[5];
        rz(pi/4) q[5];
        ry(pi/2) q[5];
        rx(pi) q[5];
        rz(pi/4) q[5];
        rz(pi/8) q[6];
        rz(pi/16) q[7];
        rz(pi/32) q[8];
        rz(pi/64) q[9];
        cx q[9],q[4];
        rz(-pi/64) q[4];
        cx q[9],q[4];
        rz(pi/64) q[4];
        cx q[8],q[4];
        rz(-pi/32) q[4];
        cx q[8],q[4];
        rz(pi/32) q[4];
        cx q[7],q[4];
        rz(-pi/16) q[4];
        cx q[7],q[4];
        rz(pi/16) q[4];
        cx q[6],q[4];
        rz(-pi/8) q[4];
        cx q[6],q[4];
        rz(pi/8) q[4];
        cx q[5],q[4];
        rz(-pi/4) q[4];
        cx q[5],q[4];
        rz(pi/4) q[4];
        ry(pi/2) q[4];
        rx(pi) q[4];
        rz(pi/4) q[4];
        rz(pi/8) q[5];
        rz(pi/16) q[6];
        rz(pi/32) q[7];
        rz(pi/64) q[8];
        rz(pi/128) q[9];
        cx q[9],q[3];
        rz(-pi/128) q[3];
        cx q[9],q[3];
        rz(pi/128) q[3];
        cx q[8],q[3];
        rz(-pi/64) q[3];
        cx q[8],q[3];
        rz(pi/64) q[3];
        cx q[7],q[3];
        rz(-pi/32) q[3];
        cx q[7],q[3];
        rz(pi/32) q[3];
        cx q[6],q[3];
        rz(-pi/16) q[3];
        cx q[6],q[3];
        rz(pi/16) q[3];
        cx q[5],q[3];
        rz(-pi/8) q[3];
        cx q[5],q[3];
        rz(pi/8) q[3];
        cx q[4],q[3];
        rz(-pi/4) q[3];
        cx q[4],q[3];
        rz(pi/4) q[3];
        ry(pi/2) q[3];
        rx(pi) q[3];
        rz(pi/4) q[3];
        rz(pi/8) q[4];
        rz(pi/16) q[5];
        rz(pi/32) q[6];
        rz(pi/64) q[7];
        rz(pi/128) q[8];
        rz(pi/256) q[9];
        cx q[9],q[2];
        rz(-pi/256) q[2];
        cx q[9],q[2];
        rz(pi/256) q[2];
        cx q[8],q[2];
        rz(-pi/128) q[2];
        cx q[8],q[2];
        rz(pi/128) q[2];
        cx q[7],q[2];
        rz(-pi/64) q[2];
        cx q[7],q[2];
        rz(pi/64) q[2];
        cx q[6],q[2];
        rz(-pi/32) q[2];
        cx q[6],q[2];
        rz(pi/32) q[2];
        cx q[5],q[2];
        rz(-pi/16) q[2];
        cx q[5],q[2];
        rz(pi/16) q[2];
        cx q[4],q[2];
        rz(-pi/8) q[2];
        cx q[4],q[2];
        rz(pi/8) q[2];
        cx q[3],q[2];
        rz(-pi/4) q[2];
        cx q[3],q[2];
        rz(pi/4) q[2];
        ry(pi/2) q[2];
        rx(pi) q[2];
        rz(pi/4) q[2];
        rz(pi/8) q[3];
        rz(pi/16) q[4];
        rz(pi/32) q[5];
        rz(pi/64) q[6];
        rz(pi/128) q[7];
        rz(pi/256) q[8];
        rz(pi/512) q[9];
        cx q[9],q[1];
        rz(-pi/512) q[1];
        cx q[9],q[1];
        rz(pi/512) q[1];
        cx q[8],q[1];
        rz(-pi/256) q[1];
        cx q[8],q[1];
        rz(pi/256) q[1];
        cx q[7],q[1];
        rz(-pi/128) q[1];
        cx q[7],q[1];
        rz(pi/128) q[1];
        cx q[6],q[1];
        rz(-pi/64) q[1];
        cx q[6],q[1];
        rz(pi/64) q[1];
        cx q[5],q[1];
        rz(-pi/32) q[1];
        cx q[5],q[1];
        rz(pi/32) q[1];
        cx q[4],q[1];
        rz(-pi/16) q[1];
        cx q[4],q[1];
        rz(pi/16) q[1];
        cx q[3],q[1];
        rz(-pi/8) q[1];
        cx q[3],q[1];
        rz(pi/8) q[1];
        cx q[2],q[1];
        rz(-pi/4) q[1];
        cx q[2],q[1];
        rz(pi/4) q[1];
        ry(pi/2) q[1];
        rx(pi) q[1];
        rz(pi/4) q[1];
        rz(pi/8) q[2];
        rz(pi/16) q[3];
        rz(pi/32) q[4];
        rz(pi/64) q[5];
        rz(pi/128) q[6];
        rz(pi/256) q[7];
        rz(pi/512) q[8];
        rz(pi/1024) q[9];
        cx q[9],q[0];
        rz(-pi/1024) q[0];
        cx q[9],q[0];
        rz(pi/1024) q[0];
        cx q[8],q[0];
        rz(-pi/512) q[0];
        cx q[8],q[0];
        rz(pi/512) q[0];
        cx q[7],q[0];
        rz(-pi/256) q[0];
        cx q[7],q[0];
        rz(pi/256) q[0];
        cx q[6],q[0];
        rz(-pi/128) q[0];
        cx q[6],q[0];
        rz(pi/128) q[0];
        cx q[5],q[0];
        rz(-pi/64) q[0];
        cx q[5],q[0];
        rz(pi/64) q[0];
        cx q[4],q[0];
        rz(-pi/32) q[0];
        cx q[4],q[0];
        rz(pi/32) q[0];
        cx q[3],q[0];
        rz(-pi/16) q[0];
        cx q[3],q[0];
        rz(pi/16) q[0];
        cx q[2],q[0];
        rz(-pi/8) q[0];
        cx q[2],q[0];
        rz(pi/8) q[0];
        cx q[1],q[0];
        rz(-pi/4) q[0];
        cx q[1],q[0];
        rz(pi/4) q[0];
        ry(pi/2) q[0];
        rx(pi) q[0];
        cx q[0],q[9];
        cx q[1],q[8];
        cx q[2],q[7];
        cx q[3],q[6];
        cx q[4],q[5];
        cx q[5],q[4];
        cx q[4],q[5];
        cx q[6],q[3];
        cx q[3],q[6];
        cx q[7],q[2];
        cx q[2],q[7];
        cx q[8],q[1];
        cx q[1],q[8];
        cx q[9],q[0];
        cx q[0],q[9];
    """
    circuit = QiskitCircuit.from_qasm_str(qasm)

    compiled_circuit = compile(
        circuit, target_gateset=["u3", "cx"], custom_passes=[MPSPass()]
    )

    fidelity = np.vdot(
        Statevector(circuit).data, Statevector(compiled_circuit).data
    )

    assert compiled_circuit.count_ops().get("cx", 0) == 0
    assert np.abs(np.round(fidelity, decimals=10)) == 1.0


def test_compile_with_target_gateset():
    """Test that the final circuit respects the user-defined gateset, no target device"""
    circuit = QiskitCircuit(2)
    circuit.cx(0, 1)
    circuit.h(0)

    target_gateset = {
        "ry",
        "rx",
        "cz",
    }
    result_circuit = compile(
        circuit,
        target_gateset=target_gateset,
    )

    assert set(op.name for op in result_circuit).issubset(target_gateset)


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
