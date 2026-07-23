"""Unit tests for hardware/embedding.py — Phase 2."""

from __future__ import annotations

import pytest
import numpy as np
from ucc.custom_passes.spectral.hardware.embedding import (
    adjacency_to_affinity,
    normalized_laplacian,
    spectral_coordinates,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def line4():
    """Unweighted 4-qubit line graph: 0-1-2-3."""
    return {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0},
    }


@pytest.fixture
def ring4():
    """4-qubit ring graph: 0-1-2-3-0."""
    return {
        0: {1: 1.0, 3: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0, 0: 1.0},
    }


# ---------------------------------------------------------------------------
# adjacency_to_affinity
# ---------------------------------------------------------------------------


def test_affinity_values_are_in_zero_one(line4):
    affinity = adjacency_to_affinity(line4, sigma=1.0)
    for i, neighbors in affinity.items():
        for j, w in neighbors.items():
            assert 0.0 < w <= 1.0


def test_affinity_is_symmetric(line4):
    affinity = adjacency_to_affinity(line4, sigma=1.0)
    for i, neighbors in affinity.items():
        for j, w in neighbors.items():
            assert affinity[j][i] == pytest.approx(w)


def test_affinity_unit_cost_gives_exp_neg_one_over_sigma(line4):
    sigma = 2.0
    affinity = adjacency_to_affinity(line4, sigma=sigma)
    expected = np.exp(-1.0 / sigma)
    assert affinity[0][1] == pytest.approx(expected)


def test_affinity_preserves_all_edges(line4):
    affinity = adjacency_to_affinity(line4, sigma=1.0)
    assert set(affinity[1].keys()) == {0, 2}


def test_affinity_empty_graph():
    assert adjacency_to_affinity({}, sigma=1.0) == {}


# ---------------------------------------------------------------------------
# normalized_laplacian
# ---------------------------------------------------------------------------


def test_laplacian_shape(line4):
    affinity = adjacency_to_affinity(line4, sigma=1.0)
    L = normalized_laplacian(affinity)
    n = len(line4)
    assert L.shape == (n, n)


def test_laplacian_is_symmetric(line4):
    affinity = adjacency_to_affinity(line4, sigma=1.0)
    L = normalized_laplacian(affinity)
    np.testing.assert_allclose(L, L.T, atol=1e-12)


def test_laplacian_is_positive_semidefinite(line4):
    affinity = adjacency_to_affinity(line4, sigma=1.0)
    L = normalized_laplacian(affinity)
    eigenvalues = np.linalg.eigvalsh(L)
    assert np.all(eigenvalues >= -1e-10)


def test_laplacian_has_zero_eigenvalue(line4):
    """A connected graph Laplacian always has exactly one zero eigenvalue."""
    affinity = adjacency_to_affinity(line4, sigma=1.0)
    L = normalized_laplacian(affinity)
    eigenvalues = np.linalg.eigvalsh(L)
    assert np.min(np.abs(eigenvalues)) == pytest.approx(0.0, abs=1e-10)


def test_laplacian_disconnected_graph_has_two_zero_eigenvalues():
    """Disconnected graph has one zero eigenvalue per component."""
    disconnected = {
        0: {1: 1.0},
        1: {0: 1.0},
        2: {3: 1.0},
        3: {2: 1.0},
    }
    affinity = adjacency_to_affinity(disconnected, sigma=1.0)
    L = normalized_laplacian(affinity)
    eigenvalues = np.linalg.eigvalsh(L)
    near_zero = np.sum(np.abs(eigenvalues) < 1e-10)
    assert near_zero == 2


# ---------------------------------------------------------------------------
# spectral_coordinates
# ---------------------------------------------------------------------------


def test_spectral_coordinates_shape(line4):
    coords = spectral_coordinates(line4, n_components=2, sigma=1.0)
    assert coords.shape == (len(line4), 2)


def test_spectral_coordinates_one_component(line4):
    coords = spectral_coordinates(line4, n_components=1, sigma=1.0)
    assert coords.shape == (len(line4), 1)


def test_spectral_coordinates_are_real(line4):
    coords = spectral_coordinates(line4, n_components=2, sigma=1.0)
    assert np.isrealobj(coords)


def test_spectral_coordinates_line_graph_is_monotone(line4):
    """First non-trivial eigenvector of a line graph is monotone."""
    coords = spectral_coordinates(line4, n_components=1, sigma=1.0)
    values = coords[:, 0]
    diffs = np.diff(values)
    assert np.all(diffs > 0) or np.all(diffs < 0)


def test_spectral_coordinates_ring_symmetry(ring4):
    """Ring graph: all qubits should have similar spectral magnitudes."""
    coords = spectral_coordinates(ring4, n_components=2, sigma=1.0)
    norms = np.linalg.norm(coords, axis=1)
    assert np.max(norms) - np.min(norms) == pytest.approx(0.0, abs=1e-8)
