# cirq_compile.py

from common import qasm_files, log_performance
from cirq.transformers import optimize_for_target_gateset, CZTargetGateset
from qbraid.transpiler import transpile as translate

def cirq_compile(cirq_circuit):
    return optimize_for_target_gateset(cirq_circuit, gateset=CZTargetGateset())

results_log = []

for filename in qasm_files:
    with open(filename, "r") as file:
        print(f"Compiling {filename} with Cirq")
        qasm_string = file.read()
        native_circuit = translate(qasm_string, 'cirq')
        log_entry = log_performance(cirq_compile, native_circuit, "cirq")
        log_entry['circuit_name'] = filename.split('/')[-1].split('_N')[0]
        results_log.append(log_entry)

# Save results
import pandas as pd
from datetime import datetime
df = pd.DataFrame(results_log)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
df.to_csv(f"cirq_results_{timestamp}.csv", index=False)
