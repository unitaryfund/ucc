from qiskit.transpiler import Target
from qiskit.providers import Backend, BackendV2
from typing import Union


def get_target(backend_like: Union[Backend, Target]) -> Target:
    """
    Safely extracts a qiskit.transpiler.Target object from any backend-like source.

    This function provides a single, reliable interface to get a Target,
    handling modern BackendV2 objects, legacy-style BackendV1 objects, and
    raw Target objects transparently without using deprecated imports.

    Args:
        backend_like: An object representing a backend (V1, V2, or Target).

    Returns:
        A qiskit.transpiler.Target instance fully describing the backend.
    """
    if isinstance(backend_like, Target):
        # The object is already a Target.
        return backend_like

    if isinstance(backend_like, BackendV2):
        # Modern BackendV2 object: The target is a direct attribute.
        return backend_like.target

    if isinstance(backend_like, Backend):
        # Legacy BackendV1-style object: It's a Backend but not a BackendV2.
        # We must construct the Target from its configuration.
        config = backend_like.configuration()
        return Target.from_configuration(
            coupling_map=config.coupling_map,
            dt=config.dt,
            basis_gates=config.basis_gates,
        )

    raise TypeError(
        f"Unrecognized backend/target type: {type(backend_like)}. "
        "Expected a Qiskit Backend or Target instance."
    )
