"""Unit tests for ``routing/routing_state.py``."""

from __future__ import annotations

from ucc.custom_passes.spectral.routing.routing_state import RoutingState


def test_state_builds_inverse_maps():
    state = RoutingState.from_initial_layout({0: 2, 1: 0, 2: 1})

    assert state.logical_to_physical == {0: 2, 1: 0, 2: 1}
    assert state.physical_to_logical == {0: 1, 1: 2, 2: 0}


def test_swap_updates_both_directions():
    state = RoutingState.from_initial_layout({0: 2, 1: 0, 2: 1})

    state.swap(0, 2)

    assert state.logical_to_physical == {0: 0, 1: 2, 2: 1}
    assert state.physical_to_logical == {0: 0, 1: 2, 2: 1}


def test_lookup_helpers_return_current_positions():
    state = RoutingState.from_initial_layout({0: 2, 1: 0, 2: 1})

    assert state.physical_of(1) == 0
    assert state.logical_of(1) == 2


def test_front_layer_can_be_initialized_and_updated():
    state = RoutingState.from_initial_layout(
        {0: 0, 1: 1}, front_layer=[(0, 1), (1, 2)]
    )

    assert state.front_layer == [(0, 1), (1, 2)]
    state.remove_front_gate((0, 1))
    assert state.front_layer == [(1, 2)]


def test_front_gate_removal_is_idempotent():
    state = RoutingState.from_initial_layout({0: 0, 1: 1}, front_layer=[])

    state.remove_front_gate((0, 1))
    assert state.front_layer == []
