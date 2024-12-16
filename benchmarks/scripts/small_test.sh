QASM_FILE="benchpress/square_heisenberg_N100_basis_rz_rx_ry_cx.qasm"
COMPILER="ucc"

SCRIPT_DIR=$(dirname "$(realpath "$0")")
RESULTS_FOLDER="$SCRIPT_DIR/../results/test_data"
mkdir -p "$RESULTS_FOLDER"
QASM_FOLDER="$SCRIPT_DIR/../circuits/qasm2/"
full_qasm_file="$QASM_FOLDER/$QASM_FILE"

command="python3 $SCRIPT_DIR/benchmark_script.py \"$full_qasm_file\" \"$COMPILER\" \"$RESULTS_FOLDER\""

eval $command