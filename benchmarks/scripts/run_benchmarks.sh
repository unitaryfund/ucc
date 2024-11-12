#!/bin/bash

# Define the compilers and QASM files
COMPILERS=("ucc_compile.py" "pytket_compile.py" "qiskit_compile.py" "cirq_compile.py")
QASM_FILES=(
    "./circuits/qasm2/benchpress/qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/benchpress/qv_N100_12345_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/benchpress/qft_N100_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/benchpress/square_heisenberg_N100_basis_rz_rx_ry_cx.qasm"
    "./circuits/qasm2/ucc/prep_select_N25_ghz_basis_rz_rx_ry_h_cx.qasm"
    "./circuits/qasm2/ucc/qcnn_N100_7layers_basis_rz_rx_ry_h_cx.qasm"
)

# Loop over each QASM file and each compiler, running them all in parallel
for qasm_file in "${QASM_FILES[@]}"; do
    echo "Processing $qasm_file..."

    # For each compiler, run it in parallel
    for compiler in "${COMPILERS[@]}"; do
        # Run compiler script with the QASM file in background
        python "$compiler" "$qasm_file" &
    done
done

# Wait for all jobs to finish before exiting
wait
echo "All benchmarks completed."
