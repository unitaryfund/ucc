#!/bin/bash

# Define the common folder path
QASM_FOLDER="../circuits/qasm2/"

# Define your list of QASM file names (without the common path)
QASM_FILES=(
    "benchpress/qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm"
    "benchpress/qv_N100_12345_basis_rz_rx_ry_cx.qasm"
    "benchpress/qft_N100_basis_rz_rx_ry_cx.qasm"
    "benchpress/square_heisenberg_N100_basis_rz_rx_ry_cx.qasm"
    "ucc/prep_select_N25_ghz_basis_rz_rx_ry_h_cx.qasm"
    "ucc/qcnn_N100_7layers_basis_rz_rx_ry_h_cx.qasm"
)

# Define your list of compilers
COMPILERS=("ucc" "qiskit" "pytket" "cirq")

# Default parallelism 4 (can be overridden by a command line argument)
PARALLELISM="${1:-4}"
echo "Running with parallelism: $PARALLELISM"

# Function to handle the kill signal
trap 'echo "All jobs killed"; exit' SIGINT SIGTERM

# Prepare the list of commands to run in parallel
commands=()
for qasm_file in "${QASM_FILES[@]}"; do
    for compiler in "${COMPILERS[@]}"; do
        # Combine the common folder path with the QASM file
        full_qasm_file="${QASM_FOLDER}${qasm_file}"
        
        # Build the command
        command="python3 $(dirname "$0")/benchmark_script.py \"$full_qasm_file\" \"$compiler\""

        commands+=("$command")
    done
done

# Execute all the commands in parallel up to the specified number of parallel jobs
parallel -j "$PARALLELISM" ::: "${commands[@]}"
