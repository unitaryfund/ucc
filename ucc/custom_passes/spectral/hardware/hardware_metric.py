"""HardwareMetric: bundles adjacency, calibration, distances, embedding, and curve order."""

from __future__ import annotations

from dataclasses import dataclass

from ucc.custom_passes.spectral.calibration import calibration_from_properties
from ucc.custom_passes.spectral.graph import coupling_to_undirected_adjacency
from ucc.custom_passes.spectral.hardware.curves import (
    hilbert_order,
    morton_order,
    to_integer_grid,
)
from ucc.custom_passes.spectral.hardware.distances import (
    hop_distance_matrix,
    weighted_distance_matrix,
)
from ucc.custom_passes.spectral.hardware.embedding import spectral_coordinates


@dataclass(frozen=True, slots=True)
class HardwareMetric:
    """Composite hardware description used by the spectral compiler."""

    adjacency: dict[int, dict[int, float]]
    hop_distances: dict[int, dict[int, float]]
    weighted_distances: dict[int, dict[int, float]]
    spectral_coords: object
    curve_order: dict[int, int]

    @classmethod
    def from_coupling_map(
        cls,
        coupling_map,
        *,
        target=None,
        n_components: int = 2,
        sigma: float = 1.0,
        grid_size: int = 16,
        hop_weight: float = 1.0,
        error_weight: float = 1.0,
        duration_weight: float = 1.0,
        duration_scale: float | None = None,
        clamp_error: bool = False,
    ) -> "HardwareMetric":
        """Build the complete hardware metric from a coupling map.

        Args:
            coupling_map: Qiskit-like coupling map object.
            target: Reserved for future calibration-aware extensions.
            n_components: Number of spectral coordinates to compute.
            sigma: Affinity kernel width.
            grid_size: Side length for the integer grid.

        Returns:
            A fully populated ``HardwareMetric``.

        Notes:
            When ``target`` is provided, the function uses calibrated two-qubit
            instruction properties from the target to weight each hardware
            edge. Otherwise it falls back to uniform edge weights.
        """

        adjacency = coupling_to_undirected_adjacency(coupling_map)
        if target is not None:
            scale = duration_scale
            if scale is None:
                scale = float(getattr(target, "dt", 1.0) or 1.0)

            weighted_adjacency: dict[int, dict[int, float]] = {
                node: {} for node in adjacency
            }
            for source, neighbors in adjacency.items():
                for target_node in neighbors:
                    if source == target_node:
                        continue

                    best_cost = None
                    for operation_name in getattr(
                        target, "operation_names", []
                    ):
                        operation = target[operation_name]
                        properties = operation.get((source, target_node))
                        if properties is None:
                            continue

                        calibration = calibration_from_properties(
                            properties,
                            hop_cost=1.0,
                            hop_weight=hop_weight,
                            error_weight=error_weight,
                            duration_weight=duration_weight,
                            duration_scale=scale,
                            clamp_error=clamp_error,
                        )
                        if (
                            best_cost is None
                            or calibration.total_cost < best_cost
                        ):
                            best_cost = calibration.total_cost

                    weighted_adjacency[source][target_node] = (
                        float(best_cost) if best_cost is not None else 1.0
                    )
        else:
            weighted_adjacency = adjacency

        hop_distances = hop_distance_matrix(adjacency)
        weighted_distances = weighted_distance_matrix(weighted_adjacency)
        spectral_coords = spectral_coordinates(
            weighted_adjacency, n_components=n_components, sigma=sigma
        )

        if spectral_coords.size == 0:
            curve_order: dict[int, int] = {}
        else:
            grid = to_integer_grid(spectral_coords, grid_size=grid_size)
            if grid.shape[1] == 1:
                sorted_indices = sorted(
                    range(len(grid)), key=lambda i: (grid[i, 0], i)
                )
                ranks = [0] * len(grid)
                for rank, index in enumerate(sorted_indices):
                    ranks[index] = rank
            else:
                ranks = (
                    hilbert_order(grid)
                    if grid.shape[1] == 2
                    else morton_order(grid)
                )
            curve_order = {
                qubit: rank
                for qubit, rank in zip(sorted(weighted_adjacency), ranks)
            }

        return cls(
            adjacency=weighted_adjacency,
            hop_distances=hop_distances,
            weighted_distances=weighted_distances,
            spectral_coords=spectral_coords,
            curve_order=curve_order,
        )

    def curve_rank(self, qubit: int) -> int:
        """Return the curve rank of a qubit.

        Args:
            qubit: Logical or physical qubit index.

        Returns:
            The curve rank assigned to ``qubit``.
        """
        return self.curve_order[qubit]
