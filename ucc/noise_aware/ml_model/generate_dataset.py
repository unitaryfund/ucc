import argparse
import json
import numpy as np
import math
from tqdm import tqdm

from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps
from qiskit.transpiler import TranspilerError
from qiskit.converters import circuit_to_dag
from qiskit_ibm_runtime.fake_provider import FakeWashingtonV2
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit.synthesis import QDrift

# Import structured circuit generators
from qiskit.circuit.library import QFT, EfficientSU2, QuantumVolume

# Import our custom classes
from ucc.noise_aware import DeviceNoiseProfile
from ucc.noise_aware.ml_router import MLFidelityRouter

# --- HELPER FUNCTIONS ---

# --- CIRCUIT GENERATOR PORTFOLIO ---


def create_random_circuit(num_qubits: int, num_gates: int) -> QuantumCircuit:
    """Creates a circuit with random CNOTs and single-qubit gates."""
    qc = QuantumCircuit(num_qubits)
    rng = np.random.default_rng(seed=num_qubits + num_gates)
    for _ in range(num_gates):
        if num_qubits > 1 and rng.random() > 0.3:
            q1, q2 = rng.choice(num_qubits, 2, replace=False)
            qc.cx(q1, q2)
        else:
            q = rng.integers(num_qubits)
            gate_type = rng.choice(["sx", "x", "rz"])
            if gate_type == "rz":
                angle = rng.uniform(0, 2 * math.pi)
                qc.rz(angle, q)
            else:
                getattr(qc, gate_type)(q)
    return qc


def create_qft_circuit(num_qubits: int) -> QuantumCircuit:
    """Creates a QFT circuit, excellent for testing routing and structured dependencies."""
    return QFT(num_qubits, do_swaps=False, approximation_degree=0).decompose()


def create_ansatz_circuit(num_qubits: int) -> QuantumCircuit:
    """Creates a VQE-style ansatz circuit with variable depth."""
    reps = np.random.randint(1, 4)  # Randomize the depth (1 to 3 repetitions)
    return EfficientSU2(num_qubits, reps=reps).decompose()


def create_quantum_volume_circuit(num_qubits: int) -> QuantumCircuit:
    """Creates a Quantum Volume circuit, designed to stress compilers with all-to-all mixing."""
    # Quantum Volume is defined for depth=qubits
    return QuantumVolume(num_qubits, depth=num_qubits, seed=42).decompose()


def create_heisenberg_circuit(
    rows: int, cols: int, trotter_steps: int = 1
) -> QuantumCircuit:
    """
    Creates a circuit for simulating the Heisenberg spin model on a 2D square lattice.

    The Heisenberg Hamiltonian is H = J * Σ (X_i X_j + Y_i Y_j + Z_i Z_j) over all
    neighboring <i,j> pairs. This function sets the coupling strength J=1 and simulation time t=1.

    Args:
        rows: The number of rows in the square lattice.
        cols: The number of columns in the square lattice.
        trotter_steps: The number of Trotter steps for the time evolution simulation.
                       Higher steps mean a more accurate but deeper circuit.

    Returns:
        A QuantumCircuit object representing the time evolution, decomposed into
        basis gates (CNOTs and single-qubit rotations).
    """
    num_qubits = rows * cols
    if num_qubits <= 1:
        # Return an empty circuit if the lattice is too small for interactions
        return QuantumCircuit(num_qubits)

    # 1. Define the interactions (Hamiltonian terms) using Pauli strings
    pauli_list = []

    # Helper function to map (row, col) coordinates to a single qubit index
    def get_qubit_idx(r, c):
        return r * cols + c

    # Iterate over all qubits in the grid to define neighbor interactions
    for r in range(rows):
        for c in range(cols):
            # Interaction with the neighbor to the right (Horizontal)
            if c < cols - 1:
                idx1, idx2 = get_qubit_idx(r, c), get_qubit_idx(r, c + 1)
                # Ensure idx1 > idx2 for consistent Pauli string generation
                if idx1 < idx2:
                    idx1, idx2 = idx2, idx1

                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}X{'I' * (idx1 - idx2 - 1)}X{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Y{'I' * (idx1 - idx2 - 1)}Y{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Z{'I' * (idx1 - idx2 - 1)}Z{'I' * idx2}",
                        1.0,
                    )
                )

            # Interaction with the neighbor below (Vertical)
            if r < rows - 1:
                idx1, idx2 = get_qubit_idx(r, c), get_qubit_idx(r + 1, c)
                if idx1 < idx2:
                    idx1, idx2 = idx2, idx1

                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}X{'I' * (idx1 - idx2 - 1)}X{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Y{'I' * (idx1 - idx2 - 1)}Y{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Z{'I' * (idx1 - idx2 - 1)}Z{'I' * idx2}",
                        1.0,
                    )
                )

    if not pauli_list:
        return QuantumCircuit(num_qubits)

    # 2. Create the Hamiltonian operator from the list of Pauli strings
    hamiltonian = SparsePauliOp.from_list(pauli_list)

    # 3. Use a Trotterization method to create the evolution circuit.
    # We use QDrift, a simple first-order method. The `reps` argument
    # corresponds to the number of Trotter steps.
    qdrift = QDrift(reps=trotter_steps)

    # Synthesize the operator into a gate representing e^(-iHt) where t=1
    evolution_gate = qdrift.synthesize(hamiltonian)

    # 4. Wrap the synthesized evolution into a QuantumCircuit
    qc = QuantumCircuit(num_qubits, name=f"heisenberg_{rows}x{cols}")
    qc.append(evolution_gate, range(num_qubits))

    # Decompose the high-level evolution gate into CNOTs and single-qubit gates
    return qc.decompose()


def create_qcnn_circuit(num_qubits: int) -> QuantumCircuit:
    """
    Creates a Quantum Convolutional Neural Network (QCNN) circuit.

    This implements a common QCNN architecture with alternating convolutional
    and pooling layers, reducing the number of active qubits by half at each
    pooling step. The circuit is fully parameterized.

    Args:
        num_qubits: The number of input qubits. Must be a power of 2.

    Returns:
        A QuantumCircuit object representing the QCNN.

    Raises:
        ValueError: If the number of qubits is not a power of 2.
    """
    if not (num_qubits > 0 and (num_qubits & (num_qubits - 1) == 0)):
        raise ValueError("Number of qubits for QCNN must be a power of 2.")

    qc = QuantumCircuit(num_qubits, name=f"qcnn_{num_qubits}q")

    # --- Helper function for a two-qubit convolutional unit ---
    def conv_unit(params: list) -> QuantumCircuit:
        """A single parameterized 2-qubit convolutional filter."""
        # This is a standard, entangling two-qubit unitary.
        # It requires 5 parameters.
        target = QuantumCircuit(2)
        target.rz(params[0], 0)
        target.rz(params[1], 1)
        target.crx(
            params[2], 0, 1
        )  # Controlled-RX is a good entangling choice
        target.ry(params[3], 0)
        target.ry(params[4], 1)
        return target

    active_qubits = list(range(num_qubits))
    param_idx = 0

    # The hierarchical structure continues until only one qubit remains "active"
    while len(active_qubits) > 1:
        # --- 1. Convolutional Layer ---
        # Apply convolutional units to adjacent pairs of active qubits
        for i in range(0, len(active_qubits), 2):
            q1, q2 = active_qubits[i], active_qubits[i + 1]

            # Create 5 new parameters for this specific unit
            conv_params = [Parameter(f"p_{param_idx + j}") for j in range(5)]
            param_idx += 5

            conv_gate = conv_unit(conv_params).to_gate(label="Conv")
            qc.append(conv_gate, [q1, q2])

        qc.barrier()

        # --- 2. Pooling Layer ---
        # Apply a CNOT and effectively discard the target qubit for the next layer
        next_active_qubits = []
        for i in range(0, len(active_qubits), 2):
            q_control = active_qubits[i]
            q_target = active_qubits[i + 1]
            qc.cx(q_control, q_target)

            # The control qubit moves on to the next layer
            next_active_qubits.append(q_control)

        active_qubits = next_active_qubits
        if len(active_qubits) > 1:
            qc.barrier()

    return qc


# --- DATA PROCESSING LOGIC (Unchanged from before) ---
def calculate_fidelity_label(
    circuit: QuantumCircuit,
    v2p_mapping: dict,
    noise_profile: DeviceNoiseProfile,
) -> float:
    fidelity = 1.0
    for instruction in circuit.data:
        if instruction.operation.name == "cx":
            v_q1, v_q2 = instruction.qubits
            # Check if both virtual qubits are in our mapping before proceeding
            if v_q1 in v2p_mapping and v_q2 in v2p_mapping:
                p_q1, p_q2 = v2p_mapping[v_q1], v2p_mapping[v_q2]
                error, _ = noise_profile.get_gate_properties(
                    "cx", (p_q1, p_q2)
                )
                fidelity *= 1.0 - error
    return fidelity


def process_circuit(
    circuit: QuantumCircuit, backend, router_instance: MLFidelityRouter
):
    try:
        transpiled_circuit = transpile(
            circuit, backend=backend, optimization_level=3, seed_transpiler=42
        )
    except TranspilerError:
        return None

    if (
        not hasattr(transpiled_circuit, "layout")
        or transpiled_circuit.layout is None
    ):
        return None
    final_v2p_mapping = transpiled_circuit.layout.final_virtual_layout()
    dag = circuit_to_dag(transpiled_circuit)

    fidelity = calculate_fidelity_label(
        transpiled_circuit, final_v2p_mapping, router_instance.noise_profile
    )
    feature_tensor = router_instance._dag_to_feature_tensor(
        dag, final_v2p_mapping
    )

    qasm_string = str(dumps(transpiled_circuit))

    return {
        "fidelity_label": fidelity,
        "feature_tensor": feature_tensor.tolist(),
        "final_qasm": qasm_string,
        "circuit_type": circuit.name,
    }


# --- MAIN EXECUTION BLOCK ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a diverse fidelity dataset for the CircuitFormer model."
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=5000,
        help="Total number of circuits to generate.",
    )
    parser.add_argument(
        "--max-qubits",
        type=int,
        default=15,
        help="Maximum number of qubits for generated circuits.",
    )
    parser.add_argument(
        "--min-qubits",
        type=int,
        default=4,
        help="Minimum number of qubits for generated circuits.",
    )
    parser.add_argument(
        "--max-seq-len",
        type=str,
        default=512,
        help="same size with model_seq_len",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="diverse_fidelity_dataset.json",
        help="Name of the output JSON file.",
    )
    args = parser.parse_args()

    print("--- Initializing Backend and Noise Models ---")
    backend = FakeWashingtonV2()
    noise_profile = DeviceNoiseProfile(backend.target)
    print(
        f"Initialized with backend: {backend.name} ({backend.num_qubits} qubits)"
    )

    router_for_feature_extraction = MLFidelityRouter(
        backend.target,
        model=None,
        noise_profile=noise_profile,
        max_seq_len=args.max_seq_len,
    )
    print(
        f"Feature vector dimension is set to: {router_for_feature_extraction.FEATURE_DIM}"
    )

    # --- The "Recipe" for Our Dataset ---
    # We define a portfolio of generators and the probability of choosing each one.
    # This ensures a diverse mix of circuit types.
    circuit_generators = {
        "random": (create_random_circuit, 0.10),  # 10% chance
        "qft": (create_qft_circuit, 0.30),  # 30% chance
        "ansatz": (create_ansatz_circuit, 0.25),  # 25% chance
        "qv": (create_quantum_volume_circuit, 0.1),  # 10% chance
        "qcnn": (create_qcnn_circuit, 0.15),  # 20% chance
        "heisenberg": (create_heisenberg_circuit, 0.10),  # 15% chance
    }
    generator_names, generator_params = zip(*circuit_generators.items())
    generator_funcs, generator_weights = zip(*generator_params)

    dataset = []
    print(
        f"\n--- Generating {args.num_samples} Data Samples from Diverse Portfolio ---"
    )

    master_rng = np.random.default_rng(seed=42)

    for _ in tqdm(range(args.num_samples), desc="Generating Circuits"):
        generator_name = master_rng.choice(
            generator_names, p=generator_weights
        )
        generator_func = circuit_generators[generator_name][0]

        if generator_name == "heisenberg":
            # Generate a random square-ish lattice
            rows = master_rng.integers(2, 6)
            cols = master_rng.integers(2, 6)
            num_qubits = rows * cols
            if num_qubits > args.max_qubits:
                continue  # Skip if too large
            trotter_steps = master_rng.integers(1, 4)
            raw_circuit = generator_func(rows, cols, trotter_steps)
            raw_circuit.name = f"heisenberg_{rows}x{cols}_{trotter_steps}steps"

        elif generator_name == "qcnn":
            # QCNNs need a number of qubits that is a power of 2
            possible_qubit_counts = [4, 8, 16, 32, 64]
            valid_qubit_counts = [
                q
                for q in possible_qubit_counts
                if args.min_qubits <= q <= args.max_qubits
            ]
            if not valid_qubit_counts:
                continue  # Skip if no valid sizes
            num_qubits = master_rng.choice(valid_qubit_counts)
            raw_circuit = generator_func(num_qubits)
            raw_circuit.name = f"qcnn_{num_qubits}q"

        else:
            num_qubits = master_rng.integers(
                args.min_qubits, args.max_qubits + 1
            )
            if generator_name == "random":
                num_gates = master_rng.integers(num_qubits, num_qubits * 5)
                raw_circuit = generator_func(num_qubits, num_gates)
                raw_circuit.name = f"random_{num_qubits}q_{num_gates}g"
            else:
                raw_circuit = generator_func(num_qubits)
                raw_circuit.name = f"{generator_name}_{num_qubits}q"

        if raw_circuit.num_parameters > 0:
            # This circuit is a template. We need to fill in concrete values.
            # Generate random values for each parameter.
            param_values = master_rng.uniform(
                0, 2 * np.pi, raw_circuit.num_parameters
            )

            # The `parameters` attribute is an ordered set of the Parameter objects.
            # We create a dictionary mapping them to our random values.
            binding_map = dict(zip(raw_circuit.parameters, param_values))

            # `assign_parameters` returns a new, concrete circuit with the values baked in.
            raw_circuit = raw_circuit.assign_parameters(binding_map)

        # 4. Process the circuit to get our data point
        processed_data = process_circuit(
            raw_circuit, backend, router_for_feature_extraction
        )

        if processed_data:
            dataset.append(processed_data)

    # Save the complete dataset to a file
    with open(args.output_file, "w") as f:
        json.dump(dataset, f, indent=2)

    print("\n--- Dataset Generation Complete ---")
    print(f"Successfully created {len(dataset)} samples.")
    print(f"Saved to '{args.output_file}'")

    import re
    from collections import Counter

    # Use regex to split on '-' or '_'
    circuit_types = [re.split("[-_]", d["circuit_type"])[0] for d in dataset]
    print("\nDataset Composition:")
    for name, count in Counter(circuit_types).items():
        # Increase precision if needed
        print(
            f"- {name}: {count} samples ({(count / len(dataset) * 100):.1f}%)"
        )
