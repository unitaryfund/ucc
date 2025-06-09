# --- Imports ---
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager, CouplingMap, Layout

# IMPORTANT: Import TrivialLayout and SabreSwap (as a baseline)
from qiskit.transpiler.passes import (
    SabreLayout,
    SabreSwap,
    ConsolidateBlocks,
    BasisTranslator,
    TrivialLayout,
)
from qiskit_ibm_runtime.fake_provider import FakeManilaV2
from qiskit.circuit.library import QFT
from qiskit.circuit.equivalence_library import StandardEquivalenceLibrary

from ucc.noise_aware import DeviceNoiseProfile, MLFidelityRouter
from ucc.noise_aware.backend_utils import get_target


def calculate_predicted_fidelity(
    circuit: QuantumCircuit, backend, layout: Layout
):
    """
    Calculates the predicted fidelity of a circuit using an EXPLICITLY provided layout object.
    This function is robust and correct.
    """
    target = get_target(backend)
    noise_profile = DeviceNoiseProfile(target)
    fidelity = 1.0

    if not isinstance(layout, Layout):
        print(
            f"Warning: Received an invalid layout of type {type(layout)}. Cannot calculate fidelity."
        )
        return 0.0

    native_2q_gate_name = "cx"
    for name in target.operation_names:
        try:
            if target.operation_from_name(name).num_qubits == 2:
                native_2q_gate_name = name
                break
        except (AttributeError, TypeError):
            continue

    for instruction in circuit.data:
        if instruction.operation.name == native_2q_gate_name:
            v_q1, v_q2 = instruction.qubits
            try:
                p_q1 = layout[v_q1]
                p_q2 = layout[v_q2]
                gate_qubits_physical = tuple(sorted((p_q1, p_q2)))
                error = noise_profile.cnot_errors.get(
                    gate_qubits_physical, 0.1
                )
                fidelity *= 1.0 - error
            except KeyError:
                continue

    return fidelity


# --- The Main Benchmark ---
if __name__ == "__main__":
    backend = FakeManilaV2()

    # Use a more complex circuit for a better test
    qc = QFT(5, do_swaps=False).decompose()

    print("--- Original Circuit ---")
    print(qc.draw(fold=-1))

    # --- Qiskit's Method (SabreSwap is the real competitor to your pass) ---
    print("\nRunning Qiskit's SabreSwap...")
    target = get_target(backend)
    # This is a minimal pipeline equivalent to what your pass does.
    qiskit_pm = PassManager(
        [
            TrivialLayout(
                coupling_map=target.build_coupling_map()
            ),  # Start with a simple layout
            SabreSwap(
                target.build_coupling_map(), heuristic="decay"
            ),  # Qiskit's standard router
            BasisTranslator(
                StandardEquivalenceLibrary, list(target.operation_names)
            ),
        ]
    )
    qiskit_compiled_qc = qiskit_pm.run(qc.copy())
    qiskit_layout = qiskit_pm.property_set["layout"]
    qiskit_fidelity = calculate_predicted_fidelity(
        qiskit_compiled_qc, backend, qiskit_layout
    )

    print("\n--- Qiskit SabreSwap Compiled Circuit ---")
    print(qiskit_compiled_qc.draw(fold=-1))
    print(f"Gate Count: {qiskit_compiled_qc.count_ops()}")
    print(f"Predicted Fidelity: {qiskit_fidelity:.4f}")

    # --- Our Method ---
    print("\nRunning Our Noise-Aware Pipeline...")

    noise_profile = DeviceNoiseProfile(target)
    coupling_map = target.build_coupling_map()

    # --- Step 1: Get the required arguments for BasisTranslator ---
    equiv_lib = StandardEquivalenceLibrary
    basis_gates = list(target.operation_names)

    # This is the correct pipeline to test YOUR router
    pass_list = [
        # Stage 1: Layout - Find an initial mapping.
        SabreLayout(CouplingMap(coupling_map), skip_routing=True),
        # Stage 2: Routing - Choose your desired routing pass.
        # Let's use our best heuristic pass for this definitive test.
        # Or, once the model is trained:
        MLFidelityRouter(target),
        # Stage 3: Optimization - Clean up the circuit after routing.
        ConsolidateBlocks(),
        # Stage 4: Final Translation - Use the correct, explicit arguments.
        BasisTranslator(
            equivalence_library=equiv_lib, target_basis=basis_gates
        ),
    ]

    # --- Step 3: Create and Run the PassManager ---
    our_pm = PassManager(pass_list)

    our_compiled_qc = our_pm.run(qc.copy())
    our_layout = our_pm.property_set["layout"]
    our_fidelity = calculate_predicted_fidelity(
        our_compiled_qc, backend, our_layout
    )

    print("\n--- Our Noise-Aware Compiled Circuit ---")
    print(our_compiled_qc.draw(fold=-1))
    print(f"Gate Count: {our_compiled_qc.count_ops()}")
    print(f"Predicted Fidelity: {our_fidelity:.4f}")

    # --- Comparison ---
    if our_fidelity > qiskit_fidelity:
        print(
            "\nSUCCESS: Our pass produced a higher fidelity circuit than SabreSwap!"
        )
    else:
        print(
            "\nNEEDS WORK: Qiskit's SabreSwap produced a higher or equal fidelity circuit."
        )
