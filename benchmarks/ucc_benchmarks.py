#!/usr/bin/env python
# coding: utf-8

# # UCC benchmarks
# In this notebook, we benchmark the performance of Unitary Fund's UCC compiler against qiskit, PyTKET and Cirq across a range of benchmarks for circuits of (100 qubits) each unless otherwise marked: 
# 
# - Quantum Approximate Optimization Algorithm (QAOA)
# - Quantum volume  (QV) calculation
# - Quantum Fourier transform (QFT)
# - Square Heisenberg model Trotterized Hamiltonian simulation
# - Quantum computational neural network (QCNN)
# - PREPARE & SELECT on a 25 qubit GHZ state


folder = "./circuits/qasm2/"

qasm_files = [folder + file for file in [
    "benchpress/qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm",
    "benchpress/qv_N100_12345_basis_rz_rx_ry_cx.qasm",
    "benchpress/qft_N100_basis_rz_rx_ry_cx.qasm",
    "benchpress/square_heisenberg_N100_basis_rz_rx_ry_cx.qasm",
    "ucc/prep_select_N25_ghz_basis_rz_rx_ry_h_cx.qasm",
    "ucc/qcnn_N100_7layers_basis_rz_rx_ry_h_cx.qasm"
    ]]


# In[2]:


from qiskit import transpile as qiskit_transpile


def qiskit_compile(qiskit_circuit):
    """Compile given qiskit.QuantumCircuit object and return the compiled circuit and total number of raw and compiled 2 qubit gates"""
    compiled_circuit = qiskit_transpile(qiskit_circuit, optimization_level=3, basis_gates=['rz', 'rx', 'ry', 'h', 'cx'])
    
    return compiled_circuit


# In[3]:


from cirq.transformers import optimize_for_target_gateset, CZTargetGateset


def cirq_compile(cirq_circuit):
    """Compile given cirq.Circuit object and return the compiled circuit and total number of raw and compiled 2 qubit gates"""
    # Compiler passes
    compiled_circuit = optimize_for_target_gateset(
    cirq_circuit, 
    gateset=CZTargetGateset() 
    )

    return compiled_circuit


# In[4]:


# Compile using TKET
from pytket.circuit import OpType
from pytket.predicates import CompilationUnit
from pytket.passes import SequencePass, DecomposeBoxes, auto_rebase_pass, SimplifyInitial, RemoveRedundancies, FullPeepholeOptimise
from pytket.transform import Transform
 
def pytket_compile(pytket_circuit):
    """Compile given pytket.Circuit object and return the compiled circuit and total number of raw and compiled 2 qubit gates"""
    compilation_unit = CompilationUnit(pytket_circuit)

    seqpass = SequencePass([
        # Remove identity and redundant gates
        SimplifyInitial(),   
        # Decompose multi-qubit gates into CNOTs and single-qubit gates
        DecomposeBoxes(),
        # Rebase the circuit to a target gate set: {Rx, Ry, Rz, CX, H}.
        RemoveRedundancies(),  # Remove any remaining redundant gates
        auto_rebase_pass(
            {OpType.Rx, OpType.Ry, OpType.Rz, OpType.CX, OpType.H}),  
        # FullPeepholeOptimise(), # Very slow, extensive optimization
    ])
    
    seqpass.apply(compilation_unit) # In-place

    compiled_circuit = compilation_unit.circuit

    return compiled_circuit


# In[5]:


from ucc import compile 

def ucc_compile(circuit):
    """Compile given qiskit.QuantumCircuit and return the compiled circuit and total number of raw and compiled 2 qubit gates"""
    compiled_circuit = compile(circuit)

    return compiled_circuit


# In[6]:


from qbraid.transpiler import transpile as translate

def get_native_rep(circuit, compiler_alias):
    """Converts the given circuit to the native representation of the given compiler using qBraid.transpile.
    """
    if alias == 'ucc':
        # Qiskit used for UCC to get raw gate counts
        native_circuit = translate(qasm_string, 'qiskit')
    else:
        native_circuit = translate(qasm_string, alias)

    return native_circuit


# In[7]:


from utils import count_multi_qubit_gates_cirq, count_multi_qubit_gates_pytket, count_multi_qubit_gates_qiskit

def count_multi_qubit_gates(circuit, compiler_alias):
    match compiler_alias:
        case 'ucc':
            result = count_multi_qubit_gates_qiskit(circuit)
        case 'qiskit':
            result = count_multi_qubit_gates_qiskit(circuit)
        case 'cirq':
            result = count_multi_qubit_gates_cirq(circuit)
        case 'pytket':
            result = count_multi_qubit_gates_pytket(circuit)
        case _:
            result = "Unknown compiler alias."

    return result


# In[8]:


from time import time

def log_performance(compiler_function, raw_circuit, compiler_alias):
    # Should also log the compiler software version
    log_entry = {"compiler": alias}
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


# In[9]:


results_log = []


# ### Profile UCC

# In[10]:


compiler_specs = [
    ('ucc', ucc_compile), 
    ('pytket', pytket_compile),
    ('qiskit', qiskit_compile),
    ('cirq', cirq_compile)
]
for filename in qasm_files:
    # Open the QASM file and read its content into a string
    with open(filename, "r") as file:
        print(filename)
        qasm_string = file.read()
        for alias, compile_func in compiler_specs:
            native_circuit = get_native_rep(qasm_string, alias)
            
            log_entry = log_performance(
                compile_func, 
                native_circuit, 
                compiler_alias=alias
                )
            log_entry['circuit_name'] = filename.split('/')[-1].split('_N')[0]
            
            results_log.append(log_entry)
            


# 

# In[11]:


import pandas as pd

# Convert results_log to a DataFrame
df = pd.DataFrame(results_log)

df['reduction_factor'] = df['raw_multiq_gates'] / df['compiled_multiq_gates'] 
df['gate_reduction_per_s'] = df['reduction_factor'] / df['compile_time']

df_og = pd.DataFrame(results_log)

df = df.groupby(["circuit_name", "compiler"]).agg(
    compile_time=("compile_time", "mean"),
    raw_multiq_gates=("raw_multiq_gates", "mean"),
    compiled_multiq_gates=("compiled_multiq_gates", "mean"),
    gate_reduction_per_s=("gate_reduction_per_s", "mean"),
    reduction_factor=("reduction_factor", "mean"),
).reset_index()



# In[12]:


from datetime import datetime

# Generate a timestamp string
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Create a filename with the timestamp
filename = f"results_{timestamp}.csv"

# Save the DataFrame as a CSV file with the timestamped filename
df.to_csv(filename, index=False)
