from time import time
import pandas as pd
from datetime import datetime

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

folder = "../circuits/qasm2/"
qasm_files = [
    folder + file
    for file in [
        "benchpress/qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm",
        "benchpress/qv_N100_12345_basis_rz_rx_ry_cx.qasm",
        "benchpress/qft_N100_basis_rz_rx_ry_cx.qasm",
        "benchpress/square_heisenberg_N100_basis_rz_rx_ry_cx.qasm",
        "ucc/prep_select_N25_ghz_basis_rz_rx_ry_h_cx.qasm",
        "ucc/qcnn_N100_7layers_basis_rz_rx_ry_h_cx.qasm",
    ]
]


def log_performance(compiler_function, raw_circuit, compiler_alias):
    log_entry = {"compiler": compiler_alias}
    log_entry["raw_multiq_gates"] = count_multi_qubit_gates(raw_circuit, compiler_alias)

    t1 = time()
    compiled_circuit = compiler_function(raw_circuit)
    t2 = time()
    log_entry["compile_time"] = t2 - t1
    log_entry["compiled_multiq_gates"] = count_multi_qubit_gates(
        compiled_circuit, compiler_alias
    )
    [
        print(f"{key}: {value}")
        for key, value in log_entry.items()
        if key != "raw_circuit"
    ]
    print("\n")

    return log_entry


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


def qiskit_compile(qiskit_circuit):
    return qiskit_transpile(
        qiskit_circuit, optimization_level=3, basis_gates=["rz", "rx", "ry", "h", "cx"]
    )


def cirq_compile(cirq_circuit):
    return optimize_for_target_gateset(cirq_circuit, gateset=CZTargetGateset())


def count_multi_qubit_gates_pytket(pytket_circuit):
    """
    Counts the number of multi-qubit operations in a given PyTket circuit.
    Args:
        circuit (Circuit): The input PyTkets circuit.
    Returns:
        int: The number of multi-qubit gates in the circuit.
    """
    multi_qubit_gate_count = pytket_circuit.n_gates - pytket_circuit.n_1qb_gates()

    return multi_qubit_gate_count


def count_multi_qubit_gates_qiskit(qiskit_circuit):
    """
    Counts the number of multi-qubit operations in the given circuit without decomposing.
    Args:
        circuit (QuantumCircuit): The input quantum circuit.
    Returns:
        int: The number of multi-qubit gates in the circuit.
    """
    multi_qubit_gate_count = 0
    
    # Iterate over each instruction in the circuit
    for instruction, _, _ in qiskit_circuit.data:
        if instruction.num_qubits > 1:
            multi_qubit_gate_count += 1

    return multi_qubit_gate_count


def count_multi_qubit_gates_cirq(cirq_circuit):
    """
    Counts the number of multi-qubit operations in a given Cirq circuit.
    Args:
        circuit (cirq.Circuit): The input Cirq circuit.
    Returns:
        int: The number of multi-qubit gates in the circuit.
    """
    multi_qubit_gate_count = 0
    
    # Iterate over each operation in the circuit
    for operation in cirq_circuit.all_operations():
        if len(operation.qubits) > 1:  # Check if the operation acts on more than one qubit
            multi_qubit_gate_count += 1

    return multi_qubit_gate_count


def count_multi_qubit_gates(circuit, compiler_alias):
    match compiler_alias:
        case "ucc":
            return count_multi_qubit_gates_qiskit(circuit)
        case "qiskit":
            return count_multi_qubit_gates_qiskit(circuit)
        case "cirq":
            return count_multi_qubit_gates_cirq(circuit)
        case "pytket":
            return count_multi_qubit_gates_pytket(circuit)
        case _:
            return "Unknown compiler alias."

def save_results(results_log, benchmark_name = "gates", folder = "../results"):
    """Save the results of the benchmarking to a CSV file.
    Parameters:
        results_log: Benchmark results. Type can be any accepted by pd.DataFrame.
        benchmark_name: Name of the benchmark to be stored as prefix to the filename. Default is "gates", other option is currently "exp-val"
        folder: Folder where the results will be stored. Default is "../results".
    """
    df = pd.DataFrame(results_log)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    df.to_csv(f"{folder}/{benchmark_name}_{timestamp}.csv", index=False)

