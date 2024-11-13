# qiskit_compile.py

from common import qasm_files, log_performance
from qiskit import transpile as qiskit_transpile
from qbraid.transpiler import transpile as translate

def qiskit_compile(qiskit_circuit):
    return qiskit_transpile(qiskit_circuit, optimization_level=3, basis_gates=['rz', 'rx', 'ry', 'h', 'cx'])

results_log = []

for filename in qasm_files:
    with open(filename, "r") as file:
        print(f"Compiling {filename} with Qiskit")
        qasm_string = file.read()
        native_circuit = translate(qasm_string, 'qiskit')
        log_entry = log_performance(qiskit_compile, native_circuit, "qiskit")
        log_entry['circuit_name'] = filename.split('/')[-1].split('_N')[0]
        results_log.append(log_entry)

# Save results
import pandas as pd
from datetime import datetime
df = pd.DataFrame(results_log)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
df.to_csv(f"qiskit-results_{timestamp}.csv", index=False)
