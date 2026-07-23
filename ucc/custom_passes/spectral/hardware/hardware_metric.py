"""HardwareMetric: bundles adjacency, calibration, distances, embedding, and curve order."""

from __future__ import annotations

from dataclasses import dataclass

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
    ) -> "HardwareMetric":
        """Build the complete hardware metric from a coupling map.

        ``target`` is accepted for future calibration-aware extensions and is
        currently unused; the current tests exercise the no-calibration path.
        """

        adjacency = coupling_to_undirected_adjacency(coupling_map)
        hop_distances = hop_distance_matrix(adjacency)
        weighted_distances = weighted_distance_matrix(adjacency)
        spectral_coords = spectral_coordinates(
            adjacency, n_components=n_components, sigma=sigma
        )

        if spectral_coords.size == 0:
            curve_order: dict[int, int] = {}
        else:
            grid = to_integer_grid(spectral_coords, grid_size=grid_size)
            ranks = (
                hilbert_order(grid)
                if grid.shape[1] == 2
                else morton_order(grid)
            )
            curve_order = {
                qubit: rank for qubit, rank in zip(sorted(adjacency), ranks)
            }

        return cls(
            adjacency=adjacency,
            hop_distances=hop_distances,
            weighted_distances=weighted_distances,
            spectral_coords=spectral_coords,
            curve_order=curve_order,
        )

    def curve_rank(self, qubit: int) -> int:
        """Return the curve rank of a qubit."""
        return self.curve_order[qubit]
