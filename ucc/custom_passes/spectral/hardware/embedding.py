"""Graph Laplacian construction and spectral coordinate embedding.

The functions here operate on the undirected weighted adjacency mapping
produced by ``ucc.custom_passes.spectral.graph``.
"""

from __future__ import annotations

from typing import TypeAlias

import numpy as np

QubitIndex: TypeAlias = int
Adjacency: TypeAlias = dict[QubitIndex, dict[QubitIndex, float]]


def _sorted_nodes(adjacency: Adjacency) -> list[int]:
    return sorted(adjacency)


def adjacency_to_affinity(adjacency: Adjacency, sigma: float) -> Adjacency:
    """Convert edge costs to similarities with an exponential kernel."""
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    affinity: Adjacency = {node: {} for node in adjacency}
    for source, neighbors in adjacency.items():
        for target, cost in neighbors.items():
            value = float(np.exp(-float(cost) / float(sigma)))
            affinity[source][target] = value
    return affinity


def normalized_laplacian(affinity: Adjacency) -> np.ndarray:
    """Return the symmetric normalized graph Laplacian.

    Isolated vertices are assigned zero rows and columns so that they preserve
    the expected disconnected-graph behavior in the tests.
    """
    nodes = _sorted_nodes(affinity)
    n = len(nodes)
    if n == 0:
        return np.zeros((0, 0), dtype=float)

    index = {node: i for i, node in enumerate(nodes)}
    w = np.zeros((n, n), dtype=float)
    for source, neighbors in affinity.items():
        i = index[source]
        for target, weight in neighbors.items():
            j = index[target]
            w[i, j] = float(weight)

    degrees = w.sum(axis=1)
    d_inv_sqrt = np.zeros(n, dtype=float)
    nonzero = degrees > 0.0
    d_inv_sqrt[nonzero] = 1.0 / np.sqrt(degrees[nonzero])

    scale = np.outer(d_inv_sqrt, d_inv_sqrt)
    laplacian = np.eye(n, dtype=float) - scale * w
    laplacian[~nonzero, :] = 0.0
    laplacian[:, ~nonzero] = 0.0
    return laplacian


def spectral_coordinates(
    adjacency: Adjacency, *, n_components: int = 2, sigma: float = 1.0
) -> np.ndarray:
    """Return low-dimensional spectral coordinates for the graph."""
    if n_components < 1:
        raise ValueError("n_components must be at least 1")

    nodes = _sorted_nodes(adjacency)
    n = len(nodes)
    if n == 0:
        return np.zeros((0, n_components), dtype=float)

    affinity = adjacency_to_affinity(adjacency, sigma=sigma)
    laplacian = normalized_laplacian(affinity)
    eigenvalues, eigenvectors = np.linalg.eigh(laplacian)

    tol = 1e-12
    nontrivial = [i for i, value in enumerate(eigenvalues) if value > tol]
    if not nontrivial:
        return np.zeros((n, n_components), dtype=float)

    chosen = nontrivial[:n_components]
    coords = eigenvectors[:, chosen]
    if coords.ndim == 1:
        coords = coords[:, np.newaxis]
    return np.asarray(coords, dtype=float)
