"""Qiskit TransformationPass wrapper for the spectral router."""

from __future__ import annotations

from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.basepasses import TransformationPass

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.router import route
from ucc.custom_passes.spectral.routing.swap_scoring import (
    DEFAULT_SPECTRAL_WEIGHT,
)


class SpectralRoutingPass(TransformationPass):
    """Insert SWAPs according to the pure spectral router."""

    def __init__(self, spectral_weight: float = DEFAULT_SPECTRAL_WEIGHT):
        """Initialize the transformation pass with no hardware metric attached.

        Args:
            spectral_weight: Weight applied to the spectral-alignment term
                when scoring candidate SWAPs. Set to ``0.0`` to recover
                plain SABRE-style routing.
        """
        super().__init__()
        self.hardware_metric: HardwareMetric | None = None
        self.spectral_weight = spectral_weight

    def run(self, dag):
        """Route a DAG using the stored layout and hardware metric.

        Args:
            dag: Input DAG circuit.

        Returns:
            A routed DAG circuit.

        Raises:
            ValueError: If the hardware metric or layout is missing.
        """
        if self.hardware_metric is None:
            raise ValueError(
                "hardware_metric must be set before running the pass"
            )
        if "layout" not in self.property_set:
            raise ValueError("layout must be present in the property_set")

        circuit = dag_to_circuit(dag)
        routed, state = route(
            circuit,
            self.hardware_metric,
            self.property_set["layout"],
            spectral_weight=self.spectral_weight,
        )
        self.property_set["final_layout"] = Layout(
            {
                routed.qubits[logical_qubit]: physical_qubit
                for logical_qubit, physical_qubit in state.logical_to_physical.items()
            }
        )
        return circuit_to_dag(routed)
