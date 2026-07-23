"""Qiskit AnalysisPass wrapper for the spectral initial layout."""

from __future__ import annotations

from qiskit.transpiler.basepasses import AnalysisPass

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.layout.logical_graph import (
    circuit_to_interaction_graph,
)
from ucc.custom_passes.spectral.layout.placement import spectral_placement


class SpectralLayoutPass(AnalysisPass):
    """Compute and store a spectral initial layout for a DAG."""

    def __init__(self):
        super().__init__()
        self.hardware_metric: HardwareMetric | None = None

    def run(self, dag):
        if self.hardware_metric is None:
            raise ValueError(
                "hardware_metric must be set before running the pass"
            )

        logical_adj = circuit_to_interaction_graph(dag)

        logical_curve_order = {
            qubit: rank for rank, qubit in enumerate(sorted(logical_adj))
        }
        logical_metric = HardwareMetric(
            adjacency=logical_adj,
            hop_distances={},
            weighted_distances={},
            spectral_coords=object(),
            curve_order=logical_curve_order,
        )

        self.property_set["layout"] = spectral_placement(
            logical_metric, self.hardware_metric
        )
        return dag
