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
        "circuit_type": circuit.name,  # Keep track of where the circuit came from
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
        backend.target, model=None, noise_profile=noise_profile
    )
    print(
        f"Feature vector dimension is set to: {router_for_feature_extraction.FEATURE_DIM}"
    )

    # --- The "Recipe" for Our Dataset ---
    # We define a portfolio of generators and the probability of choosing each one.
    # This ensures a diverse mix of circuit types.
    circuit_generators = {
        "random": (create_random_circuit, 0.25),  # 25% chance
        "qft": (create_qft_circuit, 0.40),  # 25% chance
        "ansatz": (create_ansatz_circuit, 0.25),  # 25% chance
        "qv": (create_quantum_volume_circuit, 0.1),  # 10% chance
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

        if generator_name == "qv":
            num_qubits = master_rng.integers(args.min_qubits, 10)
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
