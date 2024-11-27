import json
import os.path
from datetime import datetime

import cirq
import pytket
from cirq.contrib.qasm_import import circuit_from_qasm
from qiskit import qasm2
from qiskit.quantum_info import Operator, Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
import numpy as np

from common import cirq_compile, pytket_compile, qiskit_compile
from ucc import compile as ucc_compile

with open("../circuits/qasm2/ucc/prep_select_N10_ghz.qasm") as f:
    qasm_string = f.read()

qiskit_circuit = qasm2.loads(qasm_string)
qiskit_circuit.save_density_matrix()

ucc_compiled = ucc_compile(qasm_string, return_format="qiskit")
ucc_compiled.save_density_matrix()

cirq_compiled = cirq.qasm(cirq_compile(circuit_from_qasm(qasm_string)))
cirq_compiled = qasm2.loads(cirq_compiled)
cirq_compiled.save_density_matrix()

qiskit_compiled = qiskit_compile(qasm2.loads(qasm_string))
qiskit_compiled.save_density_matrix()

pytket_compiled = pytket.qasm.circuit_to_qasm_str(
    pytket_compile(pytket.qasm.circuit_from_qasm_str(qasm_string))
)
pytket_compiled = qasm2.loads(pytket_compiled)
pytket_compiled.save_density_matrix()

depolarizing_noise = NoiseModel()
error = depolarizing_error(0.03, 1)
two_qubit_error = depolarizing_error(0.05, 2)
depolarizing_noise.add_all_qubit_quantum_error(error, ["u1", "u2", "u3"])
depolarizing_noise.add_all_qubit_quantum_error(two_qubit_error, ["cx"])

simulator = AerSimulator(method="density_matrix", noise_model=depolarizing_noise)


uncompiled_dm = simulator.run(qiskit_circuit).result().data()["density_matrix"]
ucc_dm = simulator.run(ucc_compiled).result().data()["density_matrix"]
cirq_dm = simulator.run(cirq_compiled).result().data()["density_matrix"]
qiskit_dm = simulator.run(qiskit_compiled).result().data()["density_matrix"]
pytket_dm = simulator.run((pytket_compiled)).result().data()["density_matrix"]

observable = Operator.from_label("ZZZZZZZZZZ")

uncompiled_expval = np.real_if_close(uncompiled_dm.expectation_value(observable)).item()
ucc_expval = np.real_if_close(ucc_dm.expectation_value(observable)).item()
cirq_expval = np.real_if_close(cirq_dm.expectation_value(observable)).item()
qiskit_expval = np.real_if_close(qiskit_dm.expectation_value(observable)).item()
pytket_expval = np.real_if_close(pytket_dm.expectation_value(observable)).item()

ideal_circuit = qasm2.loads(qasm_string)
ideal_state = Statevector.from_instruction(ideal_circuit)
ideal_expval = np.real_if_close(ideal_state.expectation_value(observable)).item()

results = {
    "ideal": ideal_expval,
    "uncompiled": {
        "expval": uncompiled_expval,
        "abs_error": abs(ideal_expval - uncompiled_expval),
        "relative_error": abs(ideal_expval - uncompiled_expval) / abs(ideal_expval),
    },
    "ucc": {
        "expval": ucc_expval,
        "abs_error": abs(ideal_expval - ucc_expval),
        "relative_error": abs(ideal_expval - ucc_expval) / abs(ideal_expval),
    },
    "cirq": {
        "expval": cirq_expval,
        "abs_error": abs(ideal_expval - cirq_expval),
        "relative_error": abs(ideal_expval - cirq_expval) / abs(ideal_expval),
    },
    "qiskit": {
        "expval": qiskit_expval,
        "abs_error": abs(ideal_expval - qiskit_expval),
        "relative_error": abs(ideal_expval - qiskit_expval) / abs(ideal_expval),
    },
    "pytket": {
        "expval": pytket_expval,
        "abs_error": abs(ideal_expval - pytket_expval),
        "relative_error": abs(ideal_expval - pytket_expval) / abs(ideal_expval),
    },
}
print(results)

filename = f"expval-results_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json"

with open(os.path.join("../results", filename), "w") as f:
    json.dump(results, f)
