"""PassManager builders for baseline and spectral pipelines."""

from __future__ import annotations

from qiskit.transpiler import PassManager, generate_preset_pass_manager

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.layout.layout_pass import SpectralLayoutPass
from ucc.custom_passes.spectral.routing.routing_pass import SpectralRoutingPass


def build_baseline_pass_manager() -> PassManager:
    """Return Qiskit's level-3 preset pass manager."""
    return generate_preset_pass_manager(optimization_level=3)


def build_spectral_pass_manager(
    hardware_metric: HardwareMetric,
) -> PassManager:
    """Return a level-3 pass manager with spectral layout and routing stages.

    Args:
        hardware_metric: Hardware description used by the custom passes.

    Returns:
        A staged pass manager that keeps Qiskit's level-3 pipeline but swaps
        in the spectral layout and routing stages.
    """
    layout_pass = SpectralLayoutPass()
    layout_pass.hardware_metric = hardware_metric

    routing_pass = SpectralRoutingPass()
    routing_pass.hardware_metric = hardware_metric

    pm = generate_preset_pass_manager(optimization_level=3)
    pm.layout = PassManager([layout_pass])
    pm.routing = PassManager([routing_pass])
    return pm
