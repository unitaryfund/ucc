import cirq
import pytket
from cirq.contrib.qasm_import import circuit_from_qasm
from qiskit.quantum_info import Operator, Statevector
from qiskit import qasm2
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from ucc import compile as ucc_compile

from common import cirq_compile, qiskit_compile, pytket_compile


with open("../circuits/qasm2/ucc/prep_select_N10_ghz.qasm") as f:
    qasm_string = f.read()

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

ucc_dm = simulator.run(ucc_compiled).result().data()["density_matrix"]
cirq_dm = simulator.run(cirq_compiled).result().data()["density_matrix"]
qiskit_dm = simulator.run(qiskit_compiled).result().data()["density_matrix"]
pytket_dm = simulator.run((pytket_compiled)).result().data()["density_matrix"]

observable = Operator.from_label("ZZZZZZZZZZ")

ucc_expval = ucc_dm.expectation_value(observable)
cirq_expval = cirq_dm.expectation_value(observable)
qiskit_expval = qiskit_dm.expectation_value(observable)
pytket_expval = pytket_dm.expectation_value(observable)

ideal_circuit = qasm2.loads(qasm_string)
ideal_state = Statevector.from_instruction(ideal_circuit)
ideal_expval = ideal_state.expectation_value(observable)

results = {
    "ucc": abs(ideal_expval - ucc_expval),
    "cirq": abs(ideal_expval - cirq_expval),
    "qiskit": abs(ideal_expval - qiskit_expval),
    "pytket": abs(ideal_expval - pytket_expval),
}

print(ideal_expval)
print(results)
