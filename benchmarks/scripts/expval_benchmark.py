import json
import os.path
from datetime import datetime

import cirq
import pytket
import qiskit
from cirq.contrib.qasm_import import circuit_from_qasm
from qiskit import qasm2
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from pandas import DataFrame
import numpy as np

from common import cirq_compile, pytket_compile, qiskit_compile, save_results
from ucc import compile as ucc_compile

# Alternate files
# "../circuits/qasm2/ucc/random_Clifford_N10_basis_rz_rx_ry_h_cx.qasm"
# "../circuits/qasm2/ucc/qcnn_N10_4layers_basis_rz_rx_ry_h_cx.qasm"
with open("../circuits/qasm2/ucc/prep_select_N10_ghz.qasm") as f:
    qasm_string = f.read()


def generate_compiled_circuits(qasm: str) -> dict[str, qiskit.QuantumCircuit]:
    """Compiles the circuit represented in a QASM string using different
    compilers before converting them all to Qiskit circuits.

    Args:
        qasm: The QASM string representing the quantum circuit to be compiled.

    Returns:
        A dictionary containing the compiled quantum circuits with keys:
        uncompiled, ucc, cirq, qiskit, pytket.
    """
    uncompiled_circuit = qasm2.loads(qasm)
    qiskit_compiled = qiskit_compile(uncompiled_circuit)
    uncompiled_circuit.save_density_matrix()
    qiskit_compiled.save_density_matrix()

    ucc_compiled = ucc_compile(qasm, return_format="qiskit")
    ucc_compiled.save_density_matrix()

    cirq_compiled = cirq.qasm(cirq_compile(circuit_from_qasm(qasm)))
    cirq_compiled_qiskit = qasm2.loads(cirq_compiled)
    cirq_compiled_qiskit.save_density_matrix()

    pytket_compiled = pytket.qasm.circuit_to_qasm_str(
        pytket_compile(pytket.qasm.circuit_from_qasm_str(qasm_string))
    )
    pytket_compiled_qiskit = qasm2.loads(pytket_compiled)
    pytket_compiled_qiskit.save_density_matrix()

    return {
        "uncompiled": uncompiled_circuit,
        "ucc": ucc_compiled,
        "cirq": cirq_compiled_qiskit,
        "qiskit": qiskit_compiled,
        "pytket": pytket_compiled_qiskit,
    }


def simulate_density_matrix(circuit: qiskit.QuantumCircuit) -> np.ndarray:
    depolarizing_noise = NoiseModel()
    error = depolarizing_error(0.03, 1)
    two_qubit_error = depolarizing_error(0.05, 2)
    depolarizing_noise.add_all_qubit_quantum_error(error, ["u1", "u2", "u3"])
    depolarizing_noise.add_all_qubit_quantum_error(two_qubit_error, ["cx"])

    simulator = AerSimulator(method="density_matrix", noise_model=depolarizing_noise)
    return simulator.run(circuit).result().data()["density_matrix"]


density_matrices = {
    compiler: simulate_density_matrix(circuit)
    for compiler, circuit in generate_compiled_circuits(qasm_string).items()
}


observable = Operator.from_label("ZZZZZZZZZZ")

expectation_values = {
    compiler: np.real(dm.expectation_value(observable))
    for compiler, dm in density_matrices.items()
}


ideal_circuit = qasm2.loads(qasm_string)
ideal_state = Statevector.from_instruction(ideal_circuit)
ideal_expval = np.real(ideal_state.expectation_value(observable))

results = [{
    "compiler":compiler,
    "expval": expval,
    "absoluate_error": abs(ideal_expval - expval),
    "relative_error": abs(ideal_expval - expval) / abs(ideal_expval),
    "ideal": ideal_expval,
    }
    for compiler, expval in expectation_values.items()
]

save_results(results, "expval")
