"""Benchmark runner for baseline and spectral compilation pipelines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Callable

from qiskit import QuantumCircuit

from ucc.benchmarks.circuits import (
    draper_adder_benchmark,
    efficient_su2_benchmark,
    qaoa_ring_benchmark,
    qft_benchmark,
    random_benchmark_circuit,
    real_amplitudes_benchmark,
)
from ucc.benchmarks.metrics import BenchmarkResult, benchmark_result
from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.pipeline.passes import (
    build_baseline_pass_manager,
    build_spectral_pass_manager,
)


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """Factory for a benchmark circuit."""

    name: str
    builder: Callable[[], QuantumCircuit]

    def build(self) -> QuantumCircuit:
        """Build the benchmark circuit."""
        return self.builder()


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """Comparison between baseline and spectral compilation results."""

    name: str
    backend_name: str | None
    baseline: BenchmarkResult
    spectral: BenchmarkResult
    baseline_seconds: float
    spectral_seconds: float

    def to_dict(self) -> dict[str, object]:
        """Convert the comparison to a JSON-friendly dictionary."""
        return {
            "name": self.name,
            "backend_name": self.backend_name,
            "baseline_seconds": self.baseline_seconds,
            "spectral_seconds": self.spectral_seconds,
            "baseline": asdict(self.baseline),
            "spectral": asdict(self.spectral),
        }


def default_benchmark_cases() -> tuple[BenchmarkCase, ...]:
    """Return a small, representative benchmark suite."""
    return (
        BenchmarkCase(
            name="random-3q",
            builder=lambda: random_benchmark_circuit(3, 4, seed=123),
        ),
        BenchmarkCase(
            name="random-5q",
            builder=lambda: random_benchmark_circuit(5, 6, seed=321),
        ),
        BenchmarkCase(name="qft-3q", builder=lambda: qft_benchmark(3)),
        BenchmarkCase(name="qft-5q", builder=lambda: qft_benchmark(5)),
        BenchmarkCase(
            name="efficient-su2-3q",
            builder=lambda: efficient_su2_benchmark(3),
        ),
        BenchmarkCase(
            name="real-amplitudes-3q",
            builder=lambda: real_amplitudes_benchmark(3),
        ),
        BenchmarkCase(
            name="qaoa-ring-3q",
            builder=lambda: qaoa_ring_benchmark(3),
        ),
        BenchmarkCase(
            name="draper-adder-2q",
            builder=lambda: draper_adder_benchmark(2),
        ),
    )


def _bind_parameters(circuit: QuantumCircuit) -> QuantumCircuit:
    """Bind circuit parameters deterministically before benchmarking."""
    if not circuit.parameters:
        return circuit

    ordered_parameters = sorted(
        circuit.parameters, key=lambda parameter: parameter.name
    )
    assignments = {
        parameter: 0.1 + 0.2 * index
        for index, parameter in enumerate(ordered_parameters)
    }
    return circuit.assign_parameters(assignments, inplace=False)


def _run_pass_manager(
    pass_manager,
    circuit: QuantumCircuit,
) -> tuple[QuantumCircuit, float]:
    """Run a pass manager and measure the elapsed time."""
    start = perf_counter()
    compiled = pass_manager.run(circuit)
    return compiled, perf_counter() - start


def _backend_name(backend) -> str | None:
    """Return a stable backend name."""
    if backend is None:
        return None

    name = getattr(backend, "name", None)
    if callable(name):
        name = name()
    return name


def _run_prepared_case(
    case_name: str,
    circuit: QuantumCircuit,
    hardware_metric: HardwareMetric,
    *,
    backend=None,
) -> BenchmarkComparison:
    """Run a prepared circuit through both benchmark pipelines."""
    if backend is not None and circuit.num_qubits > backend.num_qubits:
        backend_name = _backend_name(backend)
        raise ValueError(
            f"Benchmark {case_name} requires {circuit.num_qubits} qubits, "
            f"but backend {backend_name} only has {backend.num_qubits}"
        )

    baseline_pass_manager = build_baseline_pass_manager(backend=backend)
    spectral_pass_manager = build_spectral_pass_manager(
        hardware_metric,
        backend=backend,
    )

    baseline_circuit, baseline_seconds = _run_pass_manager(
        baseline_pass_manager, circuit.copy()
    )
    spectral_circuit, spectral_seconds = _run_pass_manager(
        spectral_pass_manager, circuit.copy()
    )

    return BenchmarkComparison(
        name=case_name,
        backend_name=_backend_name(backend),
        baseline=benchmark_result(
            circuit,
            baseline_circuit,
            name=f"{case_name}-baseline",
            check_equivalence=backend is None,
        ),
        spectral=benchmark_result(
            circuit,
            spectral_circuit,
            name=f"{case_name}-spectral",
            check_equivalence=backend is None,
        ),
        baseline_seconds=baseline_seconds,
        spectral_seconds=spectral_seconds,
    )


def run_benchmark_case(
    case: BenchmarkCase,
    hardware_metric: HardwareMetric,
    *,
    backend=None,
) -> BenchmarkComparison:
    """Run one benchmark case through baseline and spectral pipelines."""
    circuit = _bind_parameters(case.build())
    return _run_prepared_case(
        case.name,
        circuit,
        hardware_metric,
        backend=backend,
    )


def run_benchmarks(
    cases: tuple[BenchmarkCase, ...] | None = None,
    *,
    hardware_metric: HardwareMetric,
    backend=None,
) -> list[BenchmarkComparison]:
    """Run a benchmark suite and skip cases that do not fit the backend."""
    results: list[BenchmarkComparison] = []
    for case in cases if cases is not None else default_benchmark_cases():
        circuit = _bind_parameters(case.build())
        if backend is not None and circuit.num_qubits > backend.num_qubits:
            continue
        results.append(
            _run_prepared_case(
                case.name,
                circuit,
                hardware_metric,
                backend=backend,
            )
        )
    return results
