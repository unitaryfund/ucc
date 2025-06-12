from qbraid.programs.alias_manager import get_program_type_alias
from qbraid.transpiler import ConversionGraph
from qbraid.transpiler import transpile as translate
from .transpilers.ucc_defaults import UCCDefault1
from qiskit import transpile as qiskit_transpile
from qiskit.circuit.equivalence_library import StandardEquivalenceLibrary
from qiskit.transpiler import PassManager, CouplingMap
from qiskit.transpiler.passes import SabreLayout, BasisTranslator
from ucc.noise_aware import DeviceNoiseProfile, MLFidelityRouter, CircuitFormer
import torch

from .noise_aware.backend_utils import get_target


import sys
import warnings

# Specify the supported Python version range
REQUIRED_MAJOR = 3
MINOR_VERSION_MIN = 12
MINOR_VERSION_MAX = 13

current_major = sys.version_info.major
current_minor = sys.version_info.minor

if current_major != REQUIRED_MAJOR or not (
    MINOR_VERSION_MIN <= current_minor <= MINOR_VERSION_MAX
):
    warnings.warn(
        f"Warning: This package is designed for Python {REQUIRED_MAJOR}.{MINOR_VERSION_MIN}-{REQUIRED_MAJOR}.{MINOR_VERSION_MAX}. "
        f"You are using Python) {current_major}.{current_minor}."
    )
supported_circuit_formats = ConversionGraph().nodes()


def compile(
    circuit,
    return_format="original",
    target_gateset=None,
    target_device=None,
    custom_passes=None,
    noise_aware_routing=True,
):
    """Compiles the provided quantum `circuit` by translating it to a Qiskit
    circuit, transpiling it, and returning the optimized circuit in the
    specified `return_format`.

    Args:
        circuit (object): The quantum circuit to be compiled.
        return_format (str): The format in which your circuit will be returned.
            e.g., "TKET", "OpenQASM2". Check ``ucc.supported_circuit_formats``.
            Defaults to the format of the input circuit.
        target_gateset (set[str]): (optional) The gateset to compile the circuit to.
            e.g. {"cx", "rx",...}. Defaults to the gate set of the target device if
            available. If no `target_gateset` or ` target_device` is provided, the
            basis gates of the input circuit are not changed.
        target_device (qiskit.transpiler.Target): (optional) The target device to compile the circuit for. None if no device to target
        custom_passes (list[qiskit.transpiler.TransformationPass]): (optional) A list of custom passes to apply after the default s
        noise_aware_routing (bool): (optional) If True, enables a noise-aware
            layout and routing pass. Requires `target_device` to be set.
            Defaults to False.

    Returns:
        object: The compiled circuit in the specified format.
    """
    if return_format == "original":
        return_format = get_program_type_alias(circuit)

    # Translate to Qiskit Circuit object
    qiskit_circuit = translate(circuit, "qiskit")

    property_set = None

    if noise_aware_routing:
        if target_device is None:
            raise ValueError(
                "Noise-aware routing requires a `target_device` to be provided."
            )

        target = get_target(
            target_device
        )  # Use the helper to get a Target object
        noise_profile = DeviceNoiseProfile(target)

        # 1. Get the hardware coupling map for the layout pass
        coupling_map = CouplingMap(target.build_coupling_map())

        # Define the model architecture EXACTLY as you did in the training script
        # This is crucial for the weights to load correctly.
        model_params = {
            "feature_dim": 16,
            "model_dim": 256,
            "n_heads": 8,
            "n_layers": 8,
            "dropout": 0.1,
            "max_seq_len": 1024,
        }
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Instantiate the model architecture
        trained_model = CircuitFormer(**model_params).to(device)

        # Load the saved weights from your best model
        model_path = "C:/Users/junli/ucc/ucc/noise_aware/ml_model/trained_models_medium_reliable/best_model.pth"
        trained_model.load_state_dict(
            torch.load(model_path, map_location=device)
        )
        trained_model.eval()  # Set the model to evaluation mode

        # 2. Construct the list of passes for our pre-compilation
        pre_pass_list = [
            # Stage 1: Find a good initial layout.
            SabreLayout(coupling_map, skip_routing=True),
            # Stage 2: Our custom, noise-aware routing pass.
            MLFidelityRouter(
                target=target,
                model=trained_model,
                noise_profile=noise_profile,
                max_seq_len=256,
            ),
            BasisTranslator(
                StandardEquivalenceLibrary, list(target.operation_names)
            ),
        ]

        pm_pre = PassManager(pre_pass_list)
        qiskit_circuit = pm_pre.run(qiskit_circuit)
        # Our pass manager has now modified the circuit and the property_set
        property_set = pm_pre.property_set

    run_default_mapping = not noise_aware_routing
    ucc_default1 = UCCDefault1(
        target_device=target_device, add_mapping_passes=run_default_mapping
    )
    if custom_passes is not None:
        ucc_default1.pass_manager.append(custom_passes)
    compiled_circuit = ucc_default1.run(
        qiskit_circuit, property_set=property_set
    )
    final_basis = None
    if target_gateset is not None:
        final_basis = target_gateset
    elif target_device is not None:
        # This ensures we always have a valid basis if a device is present
        final_basis = get_target(target_device).operation_names

    if final_basis is not None:
        # Translate into the target device gateset; no optimization
        compiled_circuit = qiskit_transpile(
            compiled_circuit,
            basis_gates=final_basis,
            optimization_level=0,
        )
    # Translate the compiled circuit to the desired format
    final_result = translate(compiled_circuit, return_format)
    return final_result
