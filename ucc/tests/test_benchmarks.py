"""Tests for benchmark generators and backend helpers."""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.providers.fake_provider import GenericBackendV2

from ucc.benchmarks.backends import (
    backend_snapshot,
    hardware_metric_from_backend,
)
from ucc.benchmarks.circuits import (
    draper_adder_benchmark,
    efficient_su2_benchmark,
    qaoa_ring_benchmark,
    qft_benchmark,
    random_benchmark_circuit,
    real_amplitudes_benchmark,
)
from ucc.benchmarks.metrics import benchmark_result
from ucc.benchmarks.runner import run_benchmarks


def test_random_benchmark_circuit_returns_circuit():
    circuit = random_benchmark_circuit(4, 5, seed=123)
    assert circuit.num_qubits == 4
    assert circuit.depth() > 0


def test_qft_benchmark_width_matches_qubits():
    circuit = qft_benchmark(5)
    assert circuit.num_qubits == 5


def test_variational_benchmarks_width_match_qubits():
    assert efficient_su2_benchmark(6).num_qubits == 6
    assert real_amplitudes_benchmark(7).num_qubits == 7
    assert qaoa_ring_benchmark(5).num_qubits == 5


def test_draper_adder_benchmark_width_matches_qubits():
    circuit = draper_adder_benchmark(4)
    assert circuit.num_qubits >= 4


def test_backend_snapshot_uses_calibrated_target_weights():
    backend = GenericBackendV2(num_qubits=3)
    snapshot = backend_snapshot(backend)

    assert snapshot.backend_name == backend.name
    assert snapshot.num_qubits == 3
    assert len(snapshot.coupling_edges) > 0
    assert any(
        weight != 1.0
        for neighbors in snapshot.hardware_metric.adjacency.values()
        for weight in neighbors.values()
    )


def test_hardware_metric_from_backend_matches_snapshot_metric():
    backend = GenericBackendV2(num_qubits=3)
    snapshot = backend_snapshot(backend)
    metric = hardware_metric_from_backend(backend)

    assert metric.adjacency == snapshot.hardware_metric.adjacency


def test_benchmark_result_marks_equivalent_simple_circuits():
    original = QuantumCircuit(2)
    original.h(0)
    original.cx(0, 1)
    compiled = original.copy()

    result = benchmark_result(original, compiled, name="simple")

    assert result.name == "simple"
    assert result.equivalent


def test_benchmark_result_binds_parameters_deterministically():
    theta = Parameter("theta")

    original = QuantumCircuit(1)
    original.rx(theta, 0)
    compiled = original.copy()

    result = benchmark_result(original, compiled, name="parameterized")

    assert result.equivalent


def test_run_benchmarks_compares_baseline_and_spectral_pipelines():
    backend = GenericBackendV2(num_qubits=3)
    snapshot = backend_snapshot(backend)

    results = run_benchmarks(
        hardware_metric=snapshot.hardware_metric,
        backend=backend,
    )

    assert results
    assert all(result.backend_name == backend.name for result in results)
    assert all(result.baseline.depth_after >= 0 for result in results)
    assert all(result.spectral.depth_after >= 0 for result in results)
