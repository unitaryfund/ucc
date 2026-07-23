"""Unit tests for ``pipeline/passes.py``."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.transpiler import PassManager

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.layout.layout_pass import SpectralLayoutPass
from ucc.custom_passes.spectral.routing.routing_pass import SpectralRoutingPass
from ucc.custom_passes.spectral.pipeline.passes import (
    build_baseline_pass_manager,
    build_spectral_pass_manager,
)


def _flatten_tasks(tasks):
    for task in tasks:
        if isinstance(task, list):
            yield from _flatten_tasks(task)
        else:
            yield task


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


def test_baseline_builder_returns_pass_manager():
    pm = build_baseline_pass_manager()

    assert isinstance(pm, PassManager)
    assert not any(
        isinstance(pass_, (SpectralLayoutPass, SpectralRoutingPass))
        for pass_ in _flatten_tasks(pm._tasks)
    )


def test_baseline_manager_preserves_semantics_on_simple_circuit():
    pm = build_baseline_pass_manager()
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    out = pm.run(circuit)

    assert Statevector.from_instruction(circuit).equiv(
        Statevector.from_instruction(out)
    )


def test_spectral_builder_orders_layout_then_routing():
    pm = build_spectral_pass_manager(_metric())
    assert isinstance(pm.layout, PassManager)
    assert isinstance(pm.routing, PassManager)
    assert isinstance(
        list(_flatten_tasks(pm.layout._tasks))[0], SpectralLayoutPass
    )
    assert isinstance(
        list(_flatten_tasks(pm.routing._tasks))[0], SpectralRoutingPass
    )
    assert pm.translation is not None
    assert pm.optimization is not None


def test_spectral_manager_preserves_semantics():
    pm = build_spectral_pass_manager(_metric())
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 2)
    circuit.x(1)

    out = pm.run(circuit)

    assert Statevector.from_instruction(circuit).equiv(
        Statevector.from_instruction(out)
    )
