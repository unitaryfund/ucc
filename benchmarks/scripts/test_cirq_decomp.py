
from common import cirq_compile, qiskit_compile, get_native_rep

qasm_path = "/Users/jordansullivan/UnitaryFund/ucc/benchmarks/qasm_circuits/qasm2/benchpress/qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm"

with open(qasm_path) as f:
    qasm_str = f.read()

cirq_rep = get_native_rep(qasm_str, "cirq")
qiskit_rep = get_native_rep(qasm_str, "qiskit")

# CIRQ
print("cirq pre-compiled",  set(type(op.gate).__name__ for op in cirq_rep.all_operations()))
print("cirq post-compiled", set(type(op.gate).__name__ for op in cirq_compile(cirq_rep).all_operations()))

# QISKIT
print("qiskit pre-compiled",  set(qiskit_rep.count_ops().keys()))
print("qiskit post-compiled", set(qiskit_compile(qiskit_rep).count_ops().keys()))