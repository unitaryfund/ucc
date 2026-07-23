"""All-pairs hop-count and weighted shortest-path distance matrices.

Both functions accept the undirected adjacency mapping produced by
``graph.coupling_to_undirected_adjacency`` and return a full
``dict[int, dict[int, float]]`` matrix.  Unreachable pairs receive
``float("inf")``.

Uses ``rustworkx`` (bundled with Qiskit) for fast graph traversal.
"""

from __future__ import annotations

from typing import TypeAlias

import rustworkx as rx

QubitIndex: TypeAlias = int
Adjacency: TypeAlias = dict[QubitIndex, dict[QubitIndex, float]]
DistanceMatrix: TypeAlias = dict[QubitIndex, dict[QubitIndex, float]]


def _adjacency_to_pygraph(
    adjacency: Adjacency,
) -> tuple[rx.PyGraph, dict[int, int]]:
    """Convert an adjacency dict to a rustworkx PyGraph.

    Returns the graph and a mapping from qubit index to rustworkx node index
    (they may differ if qubit indices are non-contiguous).
    """
    graph = rx.PyGraph()
    qubit_to_node: dict[int, int] = {}
    for qubit in adjacency:
        qubit_to_node[qubit] = graph.add_node(qubit)
    for qubit, neighbors in adjacency.items():
        for neighbor, weight in neighbors.items():
            if qubit < neighbor:
                graph.add_edge(
                    qubit_to_node[qubit], qubit_to_node[neighbor], weight
                )
    return graph, qubit_to_node


def _full_matrix(
    adjacency: Adjacency,
    raw: dict[int, dict[int, float]],
    node_to_qubit: dict[int, int],
) -> DistanceMatrix:
    """Build a complete qubit-indexed matrix, filling unreachable pairs with inf."""
    qubits = list(adjacency.keys())
    matrix: DistanceMatrix = {q: {} for q in qubits}
    for src_qubit in qubits:
        for tgt_qubit in qubits:
            if src_qubit == tgt_qubit:
                matrix[src_qubit][tgt_qubit] = 0.0
            else:
                src_node = node_to_qubit[src_qubit]
                tgt_node = node_to_qubit[tgt_qubit]
                matrix[src_qubit][tgt_qubit] = raw.get(src_node, {}).get(
                    tgt_node, float("inf")
                )
    return matrix


def hop_distance_matrix(adjacency: Adjacency) -> DistanceMatrix:
    """Return all-pairs unweighted (hop-count) shortest-path distances.

    Parameters
    ----------
    adjacency:
        Undirected adjacency mapping as returned by
        ``coupling_to_undirected_adjacency``.

    Returns
    -------
    dict[int, dict[int, float]]
        ``matrix[i][j]`` is the minimum number of hops between qubits ``i``
        and ``j``.  Self-distances are ``0``.  Unreachable pairs are
        ``float("inf")``.
    """
    if not adjacency:
        return {}
    graph, qubit_to_node = _adjacency_to_pygraph(adjacency)
    raw = {
        src: dict(lengths)
        for src, lengths in rx.graph_all_pairs_dijkstra_path_lengths(
            graph, lambda _: 1.0
        ).items()
    }
    return _full_matrix(adjacency, raw, qubit_to_node)


def weighted_distance_matrix(adjacency: Adjacency) -> DistanceMatrix:
    """Return all-pairs calibration-weighted shortest-path distances.

    Parameters
    ----------
    adjacency:
        Undirected adjacency mapping whose edge weights represent routing
        costs (e.g. ``EdgeCalibration.total_cost``).

    Returns
    -------
    dict[int, dict[int, float]]
        ``matrix[i][j]`` is the minimum total edge cost between qubits ``i``
        and ``j``.  Self-distances are ``0``.  Unreachable pairs are
        ``float("inf")``.
    """
    if not adjacency:
        return {}
    graph, qubit_to_node = _adjacency_to_pygraph(adjacency)
    raw = {
        src: dict(lengths)
        for src, lengths in rx.graph_all_pairs_dijkstra_path_lengths(
            graph, lambda w: w
        ).items()
    }
    return _full_matrix(adjacency, raw, qubit_to_node)
