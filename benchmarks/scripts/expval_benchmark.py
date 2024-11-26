import cirq
import pytket
from cirq.contrib.qasm_import import circuit_from_qasm
from cirq.transformers import CZTargetGateset, optimize_for_target_gateset
from pytket.circuit import OpType
from pytket.passes import (
    DecomposeBoxes,
    RemoveRedundancies,
    SequencePass,
    SimplifyInitial,
    auto_rebase_pass,
)
from pytket.predicates import CompilationUnit
from qiskit import transpile as qiskit_transpile
from qiskit.quantum_info import Operator, Statevector
from qiskit import qasm2
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from ucc import compile as ucc_compile


def qiskit_compile(qiskit_circuit):
    return qiskit_transpile(
        qiskit_circuit, optimization_level=3, basis_gates=["rz", "rx", "ry", "h", "cx"]
    )


def pytket_compile(pytket_circuit):
    compilation_unit = CompilationUnit(pytket_circuit)
    seqpass = SequencePass(
        [
            SimplifyInitial(),
            DecomposeBoxes(),
            RemoveRedundancies(),
            auto_rebase_pass({OpType.Rx, OpType.Ry, OpType.Rz, OpType.CX, OpType.H}),
        ]
    )
    seqpass.apply(compilation_unit)
    return compilation_unit.circuit


def cirq_compile(cirq_circuit):
    return optimize_for_target_gateset(cirq_circuit, gateset=CZTargetGateset())


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
