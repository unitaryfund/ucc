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
from qbraid.transpiler import transpile as translate
import sys  # Add sys to accept command line arguments
from ucc import compile as ucc_compile

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


# Generalized compile function that handles Qiskit, Cirq, and PyTkets
def get_compile_function(compiler_alias):
    match compiler_alias:
        case "ucc":
            return ucc_compile
        case "pytket":
            return pytket_compile
        case "qiskit":
            return qiskit_compile
        case "cirq":
            return cirq_compile
        case _:
            raise ValueError(f"Unknown compiler alias: {compiler_alias}")


def get_native_rep(qasm_string, compiler_alias):
    """Converts the given circuit to the native representation of the given compiler using qBraid.transpile.
    Parameters:
        qasm_string: QASM string representing the circuit.
        compiler_alias: Alias of the compiler to be used for conversion.
    """
    if compiler_alias == 'ucc':
        # Qiskit used for UCC to get raw gate counts
        native_circuit = translate(qasm_string, 'qiskit')
    else:
        native_circuit = translate(qasm_string, compiler_alias)

    return native_circuit


# PyTkets compilation
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


# Qiskit compilation
def qiskit_compile(qiskit_circuit):
    return qiskit_transpile(
        qiskit_circuit, optimization_level=3, basis_gates=["rz", "rx", "ry", "h", "cx"]
    )


# Cirq compilation
def cirq_compile(cirq_circuit):
    return optimize_for_target_gateset(cirq_circuit, gateset=CZTargetGateset())


# Generalized multi-qubit gate counting function
def count_multi_qubit_gates(circuit, compiler_alias):
    match compiler_alias:
        case "ucc" | "qiskit":
            return count_multi_qubit_gates_qiskit(circuit)
        case "cirq":
            return count_multi_qubit_gates_cirq(circuit)
        case "pytket":
            return count_multi_qubit_gates_pytket(circuit)
        case _:
            return "Unknown compiler alias."


# Multi-qubit gate count for PyTkets
def count_multi_qubit_gates_pytket(pytket_circuit):
    return pytket_circuit.n_gates - pytket_circuit.n_1qb_gates()


# Multi-qubit gate count for Qiskit
def count_multi_qubit_gates_qiskit(qiskit_circuit):
    return sum(1 for instruction, _, _ in qiskit_circuit.data if instruction.num_qubits > 1)


# Multi-qubit gate count for Cirq
def count_multi_qubit_gates_cirq(cirq_circuit):
    return sum(1 for operation in cirq_circuit.all_operations() if len(operation.qubits) > 1)


# Save results to CSV
def save_results(results_log, benchmark_name="gates", folder="../results"):
    """Save the results of the benchmarking to a CSV file.
    Parameters:
        results_log: Benchmark results. Type can be any accepted by pd.DataFrame.
        benchmark_name: Name of the benchmark to be stored as prefix to the filename. Default is "gates".
        folder: Folder where the results will be stored. Default is "../results".
    """
    df = pd.DataFrame(results_log)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    df.to_csv(f"{folder}/{benchmark_name}_{timestamp}.csv", index=False)


# Read the QASM files passed as command-line arguments
def get_qasm_files():
    if len(sys.argv) < 2:
        print("No QASM files provided. Please provide them as command-line arguments.")
        sys.exit(1)
    
    return sys.argv[1:]
