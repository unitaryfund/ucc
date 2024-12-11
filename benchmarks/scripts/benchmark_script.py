# benchmark_script.py
import sys
from common import log_performance, save_results, get_compile_function, get_native_rep

# Ensure both QASM file and compiler are provided as arguments
if len(sys.argv) < 4:
    print("Usage: python3 benchmark_script.py <qasm_file> <compiler> <results_folder>")
    sys.exit(1)

# Get the QASM file, compiler, and results folder passed as command-line arguments
qasm_file = sys.argv[1]
compiler_alias = sys.argv[2]
results_folder = sys.argv[3]  # New argument for results folder

# Read the QASM file
with open(qasm_file, "r") as file:
    print(f"Compiling {qasm_file} using {compiler_alias}")
    circuit_name = qasm_file.split('/')[-1].split('_N')[0]

    # Load the QASM file and get the native representation
    qasm_string = file.read()
    native_circuit = get_native_rep(qasm_string, compiler_alias)
    compile_function = get_compile_function(compiler_alias)
    
    # Log performance 
    log_entry = log_performance(compile_function, native_circuit, compiler_alias, circuit_name)
    
    # Save the log entry (you can add it to a list if needed)
    results_log = [log_entry]

# Save the results to a CSV file
save_results(results_log, benchmark_name="gates", folder=results_folder, append=True)
