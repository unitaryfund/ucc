# ucc_compile.py

from common import qasm_files, log_performance
from ucc import compile as ucc_compile
from qbraid.transpiler import transpile as translate

results_log = []

for filename in qasm_files:
    with open(filename, "r") as file:
        print(f"Compiling {filename} with UCC")
        qasm_string = file.read()
        native_circuit = translate(qasm_string, 'qiskit')
        log_entry = log_performance(ucc_compile, native_circuit, "ucc")
        log_entry['circuit_name'] = filename.split('/')[-1].split('_N')[0]
        results_log.append(log_entry)

# Save results
import pandas as pd
from datetime import datetime
df = pd.DataFrame(results_log)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
df.to_csv(f"ucc_results_{timestamp}.csv", index=False)
