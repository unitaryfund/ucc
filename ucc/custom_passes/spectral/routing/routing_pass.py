"""Qiskit TransformationPass wrapper for the spectral router."""

from __future__ import annotations

from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler.basepasses import TransformationPass

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.router import route


class SpectralRoutingPass(TransformationPass):
    """Insert SWAPs according to the pure spectral router."""

    def __init__(self):
        super().__init__()
        self.hardware_metric: HardwareMetric | None = None

    def run(self, dag):
        if self.hardware_metric is None:
            raise ValueError(
                "hardware_metric must be set before running the pass"
            )
        if "layout" not in self.property_set:
            raise ValueError("layout must be present in the property_set")

        circuit = dag_to_circuit(dag)
        routed, state = route(
            circuit, self.hardware_metric, self.property_set["layout"]
        )
        self.property_set["final_layout"] = dict(state.logical_to_physical)
        return circuit_to_dag(routed)
