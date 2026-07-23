"""Unit tests for hardware/curves.py — Phase 2."""

from __future__ import annotations

import numpy as np
from ucc.custom_passes.spectral.hardware.curves import (
    to_integer_grid,
    hilbert_order,
    morton_order,
)


# ---------------------------------------------------------------------------
# to_integer_grid
# ---------------------------------------------------------------------------


def test_integer_grid_output_within_bounds():
    coords = np.array([[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]])
    grid = to_integer_grid(coords, grid_size=8)
    assert np.all(grid >= 0)
    assert np.all(grid < 8)


def test_integer_grid_min_maps_to_zero():
    coords = np.array([[0.0, 0.0], [1.0, 1.0]])
    grid = to_integer_grid(coords, grid_size=4)
    assert np.any(grid == 0)


def test_integer_grid_max_maps_to_grid_size_minus_one():
    coords = np.array([[0.0, 0.0], [1.0, 1.0]])
    grid = to_integer_grid(coords, grid_size=4)
    assert np.any(grid == 3)


def test_integer_grid_output_dtype_is_integer():
    coords = np.array([[0.1, 0.9], [0.5, 0.5]])
    grid = to_integer_grid(coords, grid_size=4)
    assert np.issubdtype(grid.dtype, np.integer)


def test_integer_grid_shape_preserved():
    coords = np.array([[0.0, 0.1], [0.5, 0.6], [1.0, 0.9]])
    grid = to_integer_grid(coords, grid_size=8)
    assert grid.shape == coords.shape


def test_integer_grid_single_point():
    coords = np.array([[0.5, 0.5]])
    grid = to_integer_grid(coords, grid_size=4)
    assert grid.shape == (1, 2)


# ---------------------------------------------------------------------------
# hilbert_order
# ---------------------------------------------------------------------------


def test_hilbert_order_length_matches_input():
    grid = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    order = hilbert_order(grid)
    assert len(order) == 4


def test_hilbert_order_is_permutation():
    """All ranks should be distinct for distinct grid points."""
    grid = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    order = hilbert_order(grid)
    assert len(set(order)) == len(order)


def test_hilbert_order_values_are_non_negative():
    grid = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    order = hilbert_order(grid)
    assert all(r >= 0 for r in order)


def test_hilbert_order_single_point():
    grid = np.array([[0, 0]])
    order = hilbert_order(grid)
    assert len(order) == 1


def test_hilbert_order_locality():
    """Adjacent grid points should usually receive nearby curve ranks."""
    # 2x2 grid — all four adjacent to each other; Hilbert visits each once
    grid = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    order = hilbert_order(grid)
    # The maximum rank gap between any two adjacent grid points should be ≤ 2
    # for a 2x2 grid on the Hilbert curve
    pairs = [(0, 1), (0, 2), (1, 3), (2, 3)]
    for i, j in pairs:
        assert abs(order[i] - order[j]) <= 2


# ---------------------------------------------------------------------------
# morton_order
# ---------------------------------------------------------------------------


def test_morton_order_length_matches_input():
    grid = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    order = morton_order(grid)
    assert len(order) == 4


def test_morton_order_is_permutation():
    grid = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    order = morton_order(grid)
    assert len(set(order)) == len(order)


def test_morton_order_values_are_non_negative():
    grid = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    order = morton_order(grid)
    assert all(r >= 0 for r in order)


def test_morton_order_3d():
    """Morton order works for 3-D coordinates."""
    grid = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0], [1, 0, 0]])
    order = morton_order(grid)
    assert len(order) == 4
    assert len(set(order)) == 4


def test_morton_order_single_point():
    grid = np.array([[0, 0]])
    order = morton_order(grid)
    assert len(order) == 1


def test_morton_origin_has_rank_zero():
    """The origin (all zeros) should have Morton rank 0."""
    grid = np.array([[0, 0], [1, 0], [0, 1], [1, 1]])
    order = morton_order(grid)
    origin_idx = 0
    assert order[origin_idx] == 0
