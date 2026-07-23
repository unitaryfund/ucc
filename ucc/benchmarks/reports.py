"""Markdown report helpers for benchmark runs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ucc.benchmarks.runner import BenchmarkComparison, run_benchmarks


def _render_report(
    results: list[BenchmarkComparison],
    *,
    source: str,
    backend_name: str | None,
    qubits: int | None,
) -> str:
    """Render a benchmark comparison report as markdown."""
    lines = ["## Benchmark results", ""]
    lines.append(f"**Source:** {source}")
    if backend_name is not None:
        lines.append(f"**Backend:** `{backend_name}`")
    if qubits is not None:
        lines.append(f"**Qubits:** {qubits}")
    lines.append("")
    lines.extend(
        [
            "| Case | Baseline depth | Spectral depth | Baseline 2Q | Spectral 2Q |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for result in results:
        lines.append(
            "| {name} | {baseline_depth} | {spectral_depth} | {baseline_two_qubit} | {spectral_two_qubit} |".format(
                name=result.name,
                baseline_depth=result.baseline.depth_after,
                spectral_depth=result.spectral.depth_after,
                baseline_two_qubit=result.baseline.two_qubit_after,
                spectral_two_qubit=result.spectral.two_qubit_after,
            )
        )
    return "\n".join(lines) + "\n"


def benchmark_report_filename(
    *,
    backend_name: str | None = None,
    timestamp: datetime | None = None,
) -> str:
    """Return a timestamped benchmark report filename."""
    timestamp = timestamp or datetime.now()
    prefix = timestamp.strftime("%Y-%m-%dT%H%M%S")
    if backend_name:
        return f"{prefix}-{backend_name}.md"
    return f"{prefix}.md"


def save_benchmark_report(
    results: list[BenchmarkComparison],
    output_dir: str | Path,
    *,
    source: str,
    backend_name: str | None = None,
    qubits: int | None = None,
    timestamp: datetime | None = None,
) -> Path:
    """Write a benchmark report to a fresh markdown file.

    The filename is timestamped and, if a file with the same name already
    exists, a numeric suffix is appended to keep each run distinct.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    report_name = benchmark_report_filename(
        backend_name=backend_name,
        timestamp=timestamp,
    )
    report_path = output_path / report_name
    suffix = 1
    while report_path.exists():
        report_path = (
            output_path / f"{report_path.stem}-{suffix}{report_path.suffix}"
        )
        suffix += 1

    report_path.write_text(
        _render_report(
            results,
            source=source,
            backend_name=backend_name,
            qubits=qubits,
        ),
        encoding="utf-8",
    )
    return report_path


def run_and_save_benchmark_report(
    output_dir: str | Path,
    *,
    source: str,
    hardware_metric,
    backend=None,
    cases: list | tuple | None = None,
    qubits: int | None = None,
    timestamp: datetime | None = None,
) -> Path:
    """Run the benchmark suite and save a fresh markdown report."""
    results = run_benchmarks(
        cases=tuple(cases) if cases is not None else None,
        hardware_metric=hardware_metric,
        backend=backend,
    )
    backend_name = getattr(backend, "name", None)
    if callable(backend_name):
        backend_name = backend_name()
    if qubits is None:
        qubits = getattr(backend, "num_qubits", None)
    return save_benchmark_report(
        results,
        output_dir,
        source=source,
        backend_name=backend_name,
        qubits=qubits,
        timestamp=timestamp,
    )
