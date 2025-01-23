import sys

import cirq
import pytket
import qiskit
from qiskit import qasm2
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
import numpy as np

from common import cirq_compile, pytket_compile, qiskit_compile, save_results, get_native_rep
from ucc import compile as ucc_compile

if len(sys.argv) < 4:
    print("Usage: python expval_benchmark.py <qasm_filepath> <compiler> <results_folder>")
    sys.exit(1)

qasm_path: str = sys.argv[1]
compiler_alias: str = sys.argv[2]
results_folder: str = sys.argv[3]  # New argument for results folder

with open(qasm_path) as f:
    qasm_string = f.read()

def compile_for_simulation(circuit, compiler_alias: str) -> qiskit.QuantumCircuit:
    """Compiles the circuit and converts it to qiskit so it can be run on the AerSimulator.

    Args:
        circuit: The circuit to be compiled. Can be any of the supported
            circuit representations (cirq, qiskit, pytket)
        compiler_alias: The alias of the compiler to be used for compilation.
            Can be one of "ucc", "qiskit", "cirq", "pytket", or "none".

    Returns:
        A compiled circuit having used the compiler affiliated with the
        compiler_alias.
    """
    match compiler_alias:
        case "ucc":
            ucc_compiled = ucc_compile(circuit, return_format="qiskit")
            ucc_compiled.save_density_matrix()
            return ucc_compiled

        case "pytket":
            pytket_compiled = pytket.qasm.circuit_to_qasm_str(
                pytket_compile(circuit)
            )
            pytket_compiled_qiskit = qasm2.loads(pytket_compiled)
            pytket_compiled_qiskit.save_density_matrix()
            return pytket_compiled_qiskit

        case "qiskit":
            qiskit_compiled = qiskit_compile(circuit)
            qiskit_compiled.save_density_matrix()
            return qiskit_compiled

        case "cirq":
            cirq_compiled_qasm = cirq.qasm(cirq_compile(circuit))
            cirq_compiled_qiskit = qasm2.loads(cirq_compiled_qasm)
            cirq_compiled_qiskit.save_density_matrix()
            return cirq_compiled_qiskit

        case _:
            raise ValueError(f"Unknown compiler alias: {compiler_alias}")


def simulate_density_matrix(circuit: qiskit.QuantumCircuit) -> np.ndarray:
    depolarizing_noise = NoiseModel()
    error = depolarizing_error(0.03, 1)
    two_qubit_error = depolarizing_error(0.05, 2)
    depolarizing_noise.add_all_qubit_quantum_error(error, ["u1", "u2", "u3"])
    depolarizing_noise.add_all_qubit_quantum_error(two_qubit_error, ["cx"])

    simulator = AerSimulator(method="density_matrix", noise_model=depolarizing_noise)
    return simulator.run(circuit).result().data()["density_matrix"]


native_circuit = get_native_rep(qasm_string, compiler_alias)
compiled_circuit = compile_for_simulation(native_circuit, compiler_alias)
density_matrix = simulate_density_matrix(compiled_circuit)

obs_str = "Z" * compiled_circuit.num_qubits
observable = Operator.from_label(obs_str)

compiled_ev = np.real(density_matrix.expectation_value(observable))


ideal_circuit = get_native_rep(qasm_string, "qiskit")
ideal_state = Statevector.from_instruction(ideal_circuit)
ideal_ev = np.real(ideal_state.expectation_value(observable))

results = [{
    "compiler": compiler_alias,
    "circuit_name": qasm_path.split('/')[-1].split('_N')[0],
    "observable": obs_str,
    "expval": compiled_ev,
    "absoluate_error": abs(ideal_ev - compiled_ev),
    "relative_error": abs(ideal_ev - compiled_ev) / abs(ideal_ev),
    "ideal_expval": ideal_ev,
    }
]

save_results(results, benchmark_name="expval", folder=results_folder, append=True)
