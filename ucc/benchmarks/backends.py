"""IBM Runtime backend helpers for benchmark execution."""

from __future__ import annotations

from dataclasses import dataclass

from qiskit_ibm_runtime import QiskitRuntimeService

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric


@dataclass(frozen=True, slots=True)
class IBMBackendSnapshot:
    """Summary of a real IBM backend for benchmarking."""

    backend_name: str
    num_qubits: int
    operation_names: tuple[str, ...]
    coupling_edges: tuple[tuple[int, int], ...]
    hardware_metric: HardwareMetric


def load_runtime_service(
    *,
    channel: str = "ibm_quantum_platform",
    instance: str | None = None,
    token: str | None = None,
) -> QiskitRuntimeService:
    """Load an IBM Runtime service using saved credentials or a token.

    Args:
        channel: IBM channel name, usually ``"ibm_quantum_platform"``.
        instance: Optional hub/group/project instance.
        token: Optional API token if credentials are not already saved.

    Returns:
        An authenticated ``QiskitRuntimeService``.

    Raises:
        Exception: Propagated from Qiskit if authentication fails.
    """
    kwargs = {"channel": channel}
    if instance is not None:
        kwargs["instance"] = instance
    if token is not None:
        kwargs["token"] = token
    return QiskitRuntimeService(**kwargs)


def list_ibm_backends(
    service: QiskitRuntimeService | None = None,
    *,
    operational: bool = True,
) -> list[str]:
    """List available IBM backends."""
    service = service or load_runtime_service()
    backends = service.backends(operational=operational)
    return [backend.name for backend in backends]


def load_ibm_backend(
    backend_name: str,
    service: QiskitRuntimeService | None = None,
):
    """Load a named IBM backend from the runtime service."""
    service = service or load_runtime_service()
    return service.backend(backend_name)


def backend_snapshot(backend) -> IBMBackendSnapshot:
    """Build a benchmark snapshot from a backend.

    Args:
        backend: IBM backend object exposing ``name``, ``target``, and
            ``coupling_map``.

    Returns:
        A snapshot containing the calibrated hardware metric and a few summary
        properties.
    """
    hardware_metric = HardwareMetric.from_coupling_map(
        backend.coupling_map, target=backend.target, clamp_error=True
    )
    coupling_edges = tuple(
        tuple(edge) for edge in backend.coupling_map.get_edges()
    )
    return IBMBackendSnapshot(
        backend_name=backend.name,
        num_qubits=backend.num_qubits,
        operation_names=tuple(sorted(backend.target.operation_names)),
        coupling_edges=coupling_edges,
        hardware_metric=hardware_metric,
    )


def hardware_metric_from_backend(
    backend,
) -> HardwareMetric:
    """Build a calibrated hardware metric directly from a backend."""
    return backend_snapshot(backend).hardware_metric
