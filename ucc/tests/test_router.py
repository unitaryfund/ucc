"""Unit tests for ``routing/router.py``."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit.random import random_circuit
from qiskit.quantum_info import Statevector

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.router import route


def _metric():
    adjacency = {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0},
    }
    distances = {
        0: {0: 0.0, 1: 1.0, 2: 2.0},
        1: {0: 1.0, 1: 0.0, 2: 1.0},
        2: {0: 2.0, 1: 1.0, 2: 0.0},
    }
    return HardwareMetric(
        adjacency=adjacency,
        hop_distances=distances,
        weighted_distances=distances,
        spectral_coords=object(),
        curve_order={0: 0, 1: 1, 2: 2},
    )


def _metric4():
    adjacency = {
        0: {1: 1.0},
        1: {0: 1.0, 2: 1.0},
        2: {1: 1.0, 3: 1.0},
        3: {2: 1.0},
    }
    distances = {
        0: {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        1: {0: 1.0, 1: 0.0, 2: 1.0, 3: 2.0},
        2: {0: 2.0, 1: 1.0, 2: 0.0, 3: 1.0},
        3: {0: 3.0, 1: 2.0, 2: 1.0, 3: 0.0},
    }
    return HardwareMetric(
        adjacency=adjacency,
        hop_distances=distances,
        weighted_distances=distances,
        spectral_coords=object(),
        curve_order={0: 0, 1: 1, 2: 2, 3: 3},
    )


def test_adjacent_gate_is_left_unchanged():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)

    routed, state = route(circuit, _metric(), {0: 0, 1: 1, 2: 2})

    assert routed.count_ops().get("swap", 0) == 0
    assert state.logical_to_physical == {0: 0, 1: 1, 2: 2}


def test_non_adjacent_gate_gets_routed_with_swaps():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 2)

    routed, state = route(circuit, _metric(), {0: 0, 1: 1, 2: 2})

    assert routed.count_ops().get("swap", 0) >= 1
    assert state.logical_to_physical == {0: 0, 1: 1, 2: 2}


def test_routed_circuit_preserves_semantics_on_simple_case():
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 2)
    circuit.x(1)

    routed, _ = route(circuit, _metric(), {0: 0, 1: 1, 2: 2})

    assert Statevector.from_instruction(circuit).equiv(
        Statevector.from_instruction(routed)
    )


def test_route_is_deterministic_for_same_input():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 2)
    circuit.cx(0, 1)

    first, first_state = route(circuit, _metric(), {0: 0, 1: 1, 2: 2})
    second, second_state = route(circuit, _metric(), {0: 0, 1: 1, 2: 2})

    assert first == second
    assert first_state.logical_to_physical == second_state.logical_to_physical


def test_random_circuit_preserves_semantics():
    circuit = random_circuit(
        num_qubits=4,
        depth=5,
        max_operands=2,
        measure=False,
        conditional=False,
        reset=False,
        seed=1234,
    )

    routed, _ = route(circuit, _metric4(), {0: 0, 1: 1, 2: 2, 3: 3})

    assert Statevector.from_instruction(circuit).equiv(
        Statevector.from_instruction(routed)
    )
