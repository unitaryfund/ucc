from common import qasm_files, log_performance, pytket_compile, save_results
from qbraid.transpiler import transpile as translate


results_log = []

for filename in qasm_files:
    with open(filename, "r") as file:
        print(f"Compiling {filename} with PyTKET")
        qasm_string = file.read()
        native_circuit = translate(qasm_string, "pytket")
        log_entry = log_performance(pytket_compile, native_circuit, "pytket")
        log_entry["circuit_name"] = filename.split("/")[-1].split("_N")[0]
        results_log.append(log_entry)

# Save results
save_results(results_log, "gates")