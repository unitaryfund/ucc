# common.py

from time import time
from gate_counters import count_multi_qubit_gates_cirq, count_multi_qubit_gates_pytket, count_multi_qubit_gates_qiskit

folder = "../circuits/qasm2/"
qasm_files = [folder + file for file in [
    "benchpress/qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm",
    "benchpress/qv_N100_12345_basis_rz_rx_ry_cx.qasm",
    "benchpress/qft_N100_basis_rz_rx_ry_cx.qasm",
    "benchpress/square_heisenberg_N100_basis_rz_rx_ry_cx.qasm",
    "ucc/prep_select_N25_ghz_basis_rz_rx_ry_h_cx.qasm",
    "ucc/qcnn_N100_7layers_basis_rz_rx_ry_h_cx.qasm"
]]

def log_performance(compiler_function, raw_circuit, compiler_alias):
    log_entry = {"compiler": compiler_alias}
    log_entry['raw_circuit'] = raw_circuit
    log_entry["raw_multiq_gates"] = count_multi_qubit_gates(
        raw_circuit, compiler_alias
    )

    t1 = time()
    compiled_circuit = compiler_function(raw_circuit)
    t2 = time()
    log_entry["compile_time"] = t2 - t1
    log_entry["compiled_multiq_gates"] = count_multi_qubit_gates(
        compiled_circuit, compiler_alias
    )
    [print(f"{key}: {value}") for key, value in log_entry.items() if key != 'raw_circuit']
    print('\n')
    log_entry['compiled_circuit'] = compiled_circuit
    
    return log_entry

def count_multi_qubit_gates(circuit, compiler_alias):
    match compiler_alias:
        case 'ucc':
            return count_multi_qubit_gates_qiskit(circuit)
        case 'qiskit':
            return count_multi_qubit_gates_qiskit(circuit)
        case 'cirq':
            return count_multi_qubit_gates_cirq(circuit)
        case 'pytket':
            return count_multi_qubit_gates_pytket(circuit)
        case _:
            return "Unknown compiler alias."
