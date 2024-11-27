#!/bin/bash

# Limit parallelism via an optional command-line argument (default: 4)
PARALLELISM=${1:-4}

# Trap to kill all background jobs on exit
trap "kill 0" EXIT

COMPILERS=("ucc_compile.py" "pytket_compile.py" "qiskit_compile.py" "cirq_compile.py")
QASM_FILES=(
    "./circuits/qasm2/benchpress/qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/benchpress/qv_N100_12345_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/benchpress/qft_N100_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/benchpress/square_heisenberg_N100_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/ucc/prep_select_N25_ghz_basis_rz_rx_ry_h_cx.qasm"
    "./circuits/qasm2/ucc/qcnn_N100_7layers_basis_rz_rx_ry_h_cx.qasm"
)

# Function to run a single compiler on a QASM file
run_job() {
    qasm_file=$1
    compiler=$2
    echo "Processing $qasm_file with $compiler..."
    python "$compiler" "$qasm_file"
}

# Array to track background job PIDs
job_pids=()

# Loop through QASM files and compilers
for qasm_file in "${QASM_FILES[@]}"; do
    for compiler in "${COMPILERS[@]}"; do
        # Run the job in the background
        run_job "$qasm_file" "$compiler" &
        job_pids+=($!)  # Store the PID of the background job

        # If the number of running jobs reaches the parallelism limit, wait for one to finish
        while (( ${#job_pids[@]} >= PARALLELISM )); do
            for i in "${!job_pids[@]}"; do
                if ! kill -0 "${job_pids[i]}" 2>/dev/null; then
                    unset 'job_pids[i]'  # Remove finished job from the list
                fi
            done
            sleep 0.1  # Avoid busy-waiting
        done
    done
done

# Wait for any remaining jobs to finish
for pid in "${job_pids[@]}"; do
    wait "$pid"
done

echo "All benchmarks completed."
