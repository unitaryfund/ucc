"""Hardware-coupling graph construction.

This module converts Qiskit's directed ``CouplingMap`` representation into a
deterministic, undirected adjacency mapping.
"""

from collections.abc import Iterable
from typing import Protocol, TypeAlias


QubitIndex: TypeAlias = int
Adjacency: TypeAlias = dict[QubitIndex, dict[QubitIndex, float]]


class CouplingMapLike(Protocol):
    """Minimal interface needed from :class:`qiskit.transpiler.CouplingMap`.

    Using a protocol keeps the algorithm independently unit-testable. A real
    Qiskit ``CouplingMap`` satisfies this interface, while tests can use a tiny
    fake object without importing Qiskit.
    """

    def size(self) -> int:
        """Return the number of physical qubits.

        Returns:
            Number of physical qubits in the coupling map.
        """

    def get_edges(self) -> Iterable[tuple[int, int]]:
        """Return directed physical coupling edges.

        Returns:
            Directed edges as ``(source, destination)`` pairs.
        """


def coupling_to_undirected_adjacency(
    coupling_map: CouplingMapLike,
    *,
    edge_weight: float = 1.0,
) -> Adjacency:
    """Convert a directed coupling map into an undirected adjacency mapping.

    Args:
        coupling_map: A Qiskit ``CouplingMap`` or any object exposing
            compatible ``size()`` and ``get_edges()`` methods.
        edge_weight: Uniform positive weight assigned to every undirected edge.

    Returns:
        Every physical qubit index from ``0`` through ``size() - 1`` is a key.
        For every hardware connection ``a -- b``, both ``adj[a][b]`` and
        ``adj[b][a]`` are present. Directed duplicates are collapsed.

    Raises:
        TypeError: If ``size()`` or an edge endpoint is not an integer.
        ValueError: If the qubit count is negative, the edge weight is
            non-positive, an endpoint lies outside the physical-qubit range, or
            a self-loop occurs.

    Notes:
        Directionality is intentionally discarded here. This graph represents
        physical reachability for placement and SWAP routing. Native gate
        direction can be handled by later translation/direction-correction
        passes.
    """

    number_of_qubits = coupling_map.size()

    if isinstance(number_of_qubits, bool) or not isinstance(
        number_of_qubits, int
    ):
        raise TypeError("coupling_map.size() must return an integer")

    if number_of_qubits < 0:
        raise ValueError("coupling_map.size() cannot be negative")

    if isinstance(edge_weight, bool) or not isinstance(
        edge_weight, (int, float)
    ):
        raise TypeError("edge_weight must be a real number")

    weight = float(edge_weight)
    if weight <= 0.0:
        raise ValueError("edge_weight must be positive")

    # Create all nodes before processing edges. This preserves isolated qubits,
    # which would otherwise disappear from a conventional edge-derived graph.
    adjacency: Adjacency = {qubit: {} for qubit in range(number_of_qubits)}

    for raw_edge in coupling_map.get_edges():
        try:
            source, destination = raw_edge
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Each coupling edge must contain exactly two endpoints; got {raw_edge!r}"
            ) from exc

        for endpoint_name, endpoint in (
            ("source", source),
            ("destination", destination),
        ):
            if isinstance(endpoint, bool) or not isinstance(endpoint, int):
                raise TypeError(
                    f"Edge {endpoint_name} must be an integer; got {endpoint!r}"
                )
            if not 0 <= endpoint < number_of_qubits:
                raise ValueError(
                    f"Edge endpoint {endpoint} is outside the valid range "
                    f"0..{number_of_qubits - 1}"
                )

        if source == destination:
            raise ValueError(
                f"Self-loop ({source}, {destination}) is not a valid coupling edge"
            )

        # Assignment naturally collapses duplicate edges and opposite directed
        # representations such as (0, 1) and (1, 0).
        adjacency[source][destination] = weight
        adjacency[destination][source] = weight

    # Sort neighbor dictionaries for deterministic iteration and snapshots.
    return {
        node: dict(sorted(neighbors.items()))
        for node, neighbors in sorted(adjacency.items())
    }
