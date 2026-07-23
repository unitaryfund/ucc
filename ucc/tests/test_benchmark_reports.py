"""Tests for benchmark report generation."""

from __future__ import annotations

from datetime import datetime

from ucc.benchmarks.metrics import BenchmarkResult
from ucc.benchmarks.reports import (
    benchmark_report_filename,
    run_and_save_benchmark_report,
    save_benchmark_report,
)
from ucc.benchmarks.runner import BenchmarkComparison


def _comparison(name: str = "case") -> BenchmarkComparison:
    result = BenchmarkResult(
        name=name,
        num_qubits=3,
        depth_before=10,
        depth_after=7,
        two_qubit_before=4,
        two_qubit_after=2,
        swap_after=1,
        equivalent=True,
    )
    return BenchmarkComparison(
        name=name,
        backend_name="ibm_fez",
        baseline=result,
        spectral=result,
        baseline_seconds=0.1,
        spectral_seconds=0.2,
    )


def test_benchmark_report_filename_is_timestamped():
    filename = benchmark_report_filename(
        backend_name="ibm_fez",
        timestamp=datetime(2026, 7, 23, 22, 35, 22),
    )

    assert filename == "2026-07-23T223522-ibm_fez.md"


def test_save_benchmark_report_creates_fresh_file(tmp_path):
    comparison = _comparison()

    first = save_benchmark_report(
        [comparison],
        tmp_path,
        source="IBM Runtime",
        backend_name="ibm_fez",
        qubits=156,
        timestamp=datetime(2026, 7, 23, 22, 35, 22),
    )
    second = save_benchmark_report(
        [comparison],
        tmp_path,
        source="IBM Runtime",
        backend_name="ibm_fez",
        qubits=156,
        timestamp=datetime(2026, 7, 23, 22, 35, 22),
    )

    assert first != second
    assert first.read_text(encoding="utf-8").startswith("## Benchmark results")
    assert second.name.endswith("-1.md")


def test_run_and_save_benchmark_report_writes_report(tmp_path, monkeypatch):
    comparison = _comparison("demo")

    def fake_run_benchmarks(**kwargs):
        return [comparison]

    monkeypatch.setattr(
        "ucc.benchmarks.reports.run_benchmarks", fake_run_benchmarks
    )

    path = run_and_save_benchmark_report(
        tmp_path,
        source="IBM Runtime",
        hardware_metric=object(),
        backend=type("Backend", (), {"name": "ibm_fez", "num_qubits": 156})(),
        timestamp=datetime(2026, 7, 23, 22, 40, 32),
    )

    assert path.exists()
    assert "demo" in path.read_text(encoding="utf-8")
