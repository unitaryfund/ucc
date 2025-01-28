from time import time
import platform
import os
import pandas as pd
import matplotlib
from datetime import datetime
from cirq import CZTargetGateset, optimize_for_target_gateset
from pytket.circuit import OpType
from pytket.passes import (
    DecomposeBoxes,
    RemoveRedundancies,
    SequencePass,
    SimplifyInitial,
    AutoRebase,
)
from pytket.predicates import CompilationUnit
from qiskit import transpile as qiskit_transpile
from qbraid.transpiler import transpile as translate
from qiskit import __version__ as qiskit_version
from cirq import __version__ as cirq_version
from pytket import __version__ as pytket_version
from ucc import __version__ as ucc_version

import sys  # Add sys to accept command line arguments
from ucc import compile as ucc_compile


def log_performance(compiler_function, raw_circuit, compiler_alias, circuit_name):
    log_entry = {"compiler": compiler_alias}
    log_entry["circuit_name"] = circuit_name
    
    log_entry["raw_multiq_gates"] = count_multi_qubit_gates(raw_circuit, compiler_alias)

    t1 = time()
    compiled_circuit = compiler_function(raw_circuit)
    t2 = time()
    log_entry["compile_time"] = t2 - t1
    log_entry["compiled_multiq_gates"] = count_multi_qubit_gates(
        compiled_circuit, compiler_alias
    )
    [
        print(f"{key}: {value}")
        for key, value in log_entry.items()
        if key != "raw_circuit"
    ]
    print("\n")

    return log_entry


# Generalized compile function that handles Qiskit, Cirq, and PyTkets
def get_compile_function(compiler_alias):
    match compiler_alias:
        case "ucc":
            return ucc_compile
        case "pytket":
            return pytket_compile
        case "qiskit":
            return qiskit_compile
        case "cirq":
            return cirq_compile
        case _:
            raise ValueError(f"Unknown compiler alias: {compiler_alias}")


def get_native_rep(qasm_string, compiler_alias):
    """Converts the given circuit to the native representation of the given compiler using qBraid.transpile.
    Parameters:
        qasm_string: QASM string representing the circuit.
        compiler_alias: Alias of the compiler to be used for conversion.
    """
    if compiler_alias == 'ucc':
        # Qiskit used for UCC to get raw gate counts
        native_circuit = translate(qasm_string, 'qiskit')
    else:
        native_circuit = translate(qasm_string, compiler_alias)

    return native_circuit


# PyTkets compilation
def pytket_compile(pytket_circuit):
    compilation_unit = CompilationUnit(pytket_circuit)
    seqpass = SequencePass(
        [
            SimplifyInitial(),
            DecomposeBoxes(),
            RemoveRedundancies(),
            AutoRebase({OpType.Rx, OpType.Ry, OpType.Rz, OpType.CX, OpType.H}),
        ]
    )
    seqpass.apply(compilation_unit)
    return compilation_unit.circuit


# Qiskit compilation
def qiskit_compile(qiskit_circuit):
    return qiskit_transpile(
        qiskit_circuit, optimization_level=3, basis_gates=["rz", "rx", "ry", "h", "cx"]
    )


# Cirq compilation
def cirq_compile(cirq_circuit):
    return optimize_for_target_gateset(cirq_circuit, )


# Multi-qubit gate count for PyTkets
def count_multi_qubit_gates_pytket(pytket_circuit):
    return pytket_circuit.n_gates - pytket_circuit.n_1qb_gates()


# Multi-qubit gate count for Qiskit
def count_multi_qubit_gates_qiskit(qiskit_circuit):
    return sum(1 for instruction, _, _ in qiskit_circuit.data if instruction.num_qubits > 1)


# Multi-qubit gate count for Cirq
def count_multi_qubit_gates_cirq(cirq_circuit):
    return sum(1 for operation in cirq_circuit.all_operations() if len(operation.qubits) > 1)


def count_multi_qubit_gates(circuit, compiler_alias):
    match compiler_alias:
        case "ucc" | "qiskit":
            return count_multi_qubit_gates_qiskit(circuit)
        case "cirq":
            return count_multi_qubit_gates_cirq(circuit)
        case "pytket":
            return count_multi_qubit_gates_pytket(circuit)
        case _:
            return "Unknown compiler alias."

def get_header(df):
    # Get version information for the compilers
    compiler_versions = {
        "qiskit": qiskit_version,
        "cirq": cirq_version,
        "pytket": pytket_version,
        "ucc": ucc_version,
    }

    # Create version header as a string formatted for CSV
    version_header = "# Compiler versions: " + ", ".join(
        f"{key}={value}" for key, value in compiler_versions.items()
    )

    # Get Operating System Info
    os_info = platform.system()  # OS name (e.g., 'Darwin' for macOS, 'Linux', 'Windows')
    os_version = platform.version()  # OS version
    architecture = platform.architecture()  # System architecture (e.g., '64bit')

    # Get Parallelism Info (number of CPU cores)
    cpu_count = os.cpu_count()  # Number of available CPU cores

    # Combine the information into a header
    header_info = f"OS: {os_info} {os_version}, Architecture: {architecture[0]}, CPU Cores: {cpu_count}"
    version_header += f" # {header_info}"
    return version_header

def save_results(results_log, benchmark_name="gates", folder="../results", append=False):
    """Save the results of the benchmarking to a CSV file with compiler versions as a header.
    
    Parameters:
        results_log: Benchmark results. Type can be any accepted by pd.DataFrame.
        benchmark_name: Name of the benchmark to be stored as prefix to the filename. Default is "gates".
        folder: Folder where the results will be stored. Default is "../results".
        append: Whether to append to an existing file created on the same date (if True) or overwrite (if False). Default is False.
    """
    df = pd.DataFrame(results_log)
    current_date = datetime.now().strftime("%Y-%m-%d_%H")
    os.makedirs(folder, exist_ok=True)
    file_name = f"{benchmark_name}_{current_date}.csv"
    file_path = os.path.join(folder, file_name)

    version_header = get_header(df)
    # Check if the file exists
    file_exists = os.path.exists(file_path)

    # Open the file in the appropriate mode
    with open(file_path, "a" if append else "w") as f:
        # If the file is new or being overwritten, write the version header
        if not file_exists or not append:
            f.write(f"{version_header}\n")

        # Always write the DataFrame
        df.to_csv(f, header=not file_exists or not append, index=False)

    print(f"Results saved to {file_path}")


# Read the QASM files passed as command-line arguments
def get_qasm_files():
    if len(sys.argv) < 2:
        print("No QASM files provided. Please provide them as command-line arguments.")
        sys.exit(1)
    
    return sys.argv[1:]


def annotate_and_adjust(ax, text, xy, color, previous_bboxes, offset=(0, 15), increment=5, fontsize=8, max_attempts=20):
    """
    Annotates the plot while dynamically adjusting the position to avoid overlaps. In-place operation.

    Parameters:
        ax (matplotlib.axes.Axes): The axis object to annotate.
        text (str): The annotation text.
        xy (tuple): The (x, y) coordinates for the annotation anchor point.
        color (str): The color for the text and arrow.
        previous_bboxes (list): A list to track previous annotation bounding boxes (in data coordinates).
        offset (tuple): The initial offset in points (x_offset, y_offset).
        increment (int): The vertical adjustment increment in points to resolve overlaps.
        fontsize (int): Font size of the annotation text.
        max_attempts (int): The maximum number of position adjustments to resolve overlaps.
        #TODO: Add margin parameter to adjust the bounding box size. Can be an issue when comparing dates which are strings
    Returns:
        None
    """
    # Create the annotation
    annotation = ax.annotate(
        text,
        xy,
        textcoords="offset points",
        xytext=offset,  # Default offset
        ha='center',
        fontsize=fontsize,
        color=color,
        rotation=15,
        arrowprops=dict(
            arrowstyle="->",
            color=color,
            lw=0.5,
            shrinkA=0,  # Shrink arrow length to avoid overlap
            shrinkB=5
        ),
        bbox=dict(
            boxstyle="round,pad=0.2",
            edgecolor=color,
            facecolor="white",
            alpha=0.25
        )
    )

    # Force a renderer update to ensure bounding box accuracy
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()

    # Get the bounding box of the annotation in data coordinates
    bbox = annotation.get_tightbbox(renderer).transformed(ax.transData.inverted())
    # print(f"Initial annotation: '{text}' at {xy}, bbox: {bbox}", '\n')

    attempts = 0
    current_offset = offset[1]
    # Adjust position to avoid overlap
    while any(bbox.overlaps(prev_bbox) for prev_bbox in previous_bboxes):
        for prev_bbox in previous_bboxes:
            if bbox.overlaps(prev_bbox):
                # print(f"\nOverlapping with previous annotation:\n"
                #       f"  Previous bbox: {prev_bbox}\n"
                #       f"  Annotation text: '{annotation.get_text()}'\n")
                break
        # Increase vertical offset to move annotation upward
        current_offset += increment
        annotation.set_position((offset[0], current_offset))
        
        # Force the renderer to update after position adjustment
        ax.figure.canvas.draw()
        bbox = annotation.get_tightbbox(renderer).transformed(ax.transData.inverted())

        # Update the plot to show the new position
        ax.figure.canvas.flush_events()
        # Increment the attempt counter and check for max attempts
        attempts += 1
        if attempts >= max_attempts:
            print(f"Warning: Maximum adjustment attempts reached for annotation '{text}'.")
            break

    # Add the final bounding box to the list of previous bounding boxes
    previous_bboxes.append(bbox)



def adjust_axes_to_fit_labels(ax, x_scale=1.0, y_scale=1.0, x_log=False, y_log=False):
    """
    Adjust the axes limits to ensure all labels and annotations fit within the view. In-place operation.

    Parameters:
    - ax: The Matplotlib axes object to adjust.
    - x_scale: The factor by which to expand the x-axis limits.
    - y_scale: The factor by which to expand the y-axis limits.
    - x_log: Set to True if the x-axis uses a logarithmic scale.
    - y_log: Set to True if the y-axis uses a logarithmic scale.
    """
    renderer = ax.figure.canvas.get_renderer()

    # Get the current axes limits
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    # Check the position of all annotations
    all_bboxes = [
        child.get_window_extent(renderer=renderer).transformed(ax.transData.inverted())
        for child in ax.get_children() if isinstance(child, matplotlib.text.Annotation)
    ]

    # Expand x-axis limits if annotations are off the edge
    for bbox in all_bboxes:
        if bbox.x0 < x_min:  # Left edge
            x_min = bbox.x0
        if bbox.x1 > x_max:  # Right edge
            x_max = bbox.x1

    # Expand y-axis limits if annotations are off the edge
    for bbox in all_bboxes:
        if bbox.y0 < y_min:  # Bottom edge
            y_min = bbox.y0
        if bbox.y1 > y_max:  # Top edge
            y_max = bbox.y1

    # Apply scaling factors based on whether axes are logarithmic
    if x_log:
        x_min = x_min / x_scale
        x_max = x_max * x_scale
    else:
        x_range = x_max - x_min
        x_min -= (x_scale - 1) * x_range
        x_max += (x_scale - 1) * x_range

    if y_log:
        y_min = y_min / y_scale
        y_max = y_max * y_scale
    else:
        y_range = y_max - y_min
        y_min -= (y_scale - 1) * y_range
        y_max += (y_scale - 1) * y_range

    # Set the new axis limits
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
