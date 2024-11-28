import sys
from common import log_performance, save_results, get_compile_function, get_native_rep

# Ensure both QASM file and compiler are provided as arguments
if len(sys.argv) < 3:
    print("Usage: python3 my_benchmark_script.py <qasm_file> <compiler>")
    sys.exit(1)

# Get the QASM file and compiler passed as command-line arguments
qasm_file = sys.argv[1]
compiler_alias = sys.argv[2]

# Read the QASM file
with open(qasm_file, "r") as file:
    print(f"Compiling {qasm_file} using {compiler_alias}")
    qasm_string = file.read()
    native_circuit = get_native_rep(qasm_string, compiler_alias)
    compile_function = get_compile_function(compiler_alias)
    # Log performance using the specified compiler
    log_entry = log_performance(compile_function, native_circuit, compiler_alias)
    
    # Save the log entry (you can add it to a list if needed)
    results_log = [log_entry]

# Save the results to a CSV file
save_results(results_log)
