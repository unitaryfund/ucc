"""PassManager builders for baseline and spectral pipelines."""

from __future__ import annotations

from qiskit.transpiler import PassManager, generate_preset_pass_manager

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.layout.layout_pass import SpectralLayoutPass
from ucc.custom_passes.spectral.routing.routing_pass import SpectralRoutingPass


def build_baseline_pass_manager(backend=None) -> PassManager:
    """Return Qiskit's level-3 preset pass manager.

    Args:
        backend: Optional backend used to specialize the preset pass manager.

    Returns:
        Qiskit's level-3 pass manager, optionally backend-aware.
    """
    if backend is None:
        return generate_preset_pass_manager(optimization_level=3)
    return generate_preset_pass_manager(optimization_level=3, backend=backend)


def build_spectral_pass_manager(
    hardware_metric: HardwareMetric,
    backend=None,
) -> PassManager:
    """Return a level-3 pass manager with spectral layout and routing stages.

    Args:
        hardware_metric: Hardware description used by the custom passes.
        backend: Optional backend used to specialize the preset pass manager.

    Returns:
        A staged pass manager that keeps Qiskit's level-3 pipeline but swaps
        in the spectral layout and routing stages.
    """
    layout_pass = SpectralLayoutPass()
    layout_pass.hardware_metric = hardware_metric

    routing_pass = SpectralRoutingPass()
    routing_pass.hardware_metric = hardware_metric

    if backend is None:
        pm = generate_preset_pass_manager(optimization_level=3)
    else:
        pm = generate_preset_pass_manager(
            optimization_level=3, backend=backend
        )
    pm.layout = PassManager([layout_pass])
    pm.routing = PassManager([routing_pass])
    return pm
