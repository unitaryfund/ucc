"""Pure interaction-sequence router producing a SWAP-inserted circuit."""

from __future__ import annotations

from collections import deque

from qiskit import QuantumCircuit

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.routing_state import RoutingState


def _instruction_qubits(instruction):
    """Return qubits from a Qiskit instruction record."""
    if hasattr(instruction, "qubits"):
        return list(instruction.qubits)
    return list(instruction[1])


def _instruction_operation(instruction):
    """Return the operation from a Qiskit instruction record."""
    if hasattr(instruction, "operation"):
        return instruction.operation
    return instruction[0]


def _shortest_path(
    adjacency: dict[int, dict[int, float]], start: int, goal: int
):
    """Return a shortest path in the hardware adjacency graph."""
    if start == goal:
        return [start]

    queue: deque[int] = deque([start])
    parents: dict[int, int | None] = {start: None}
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor in parents:
                continue
            parents[neighbor] = node
            if neighbor == goal:
                path = [goal]
                while path[-1] != start:
                    path.append(parents[path[-1]])
                path.reverse()
                return path
            queue.append(neighbor)
    raise ValueError("hardware graph is disconnected")


def route(
    circuit: QuantumCircuit,
    hardware_metric: HardwareMetric,
    initial_layout: dict[int, int],
):
    """Route a circuit onto the hardware graph with SWAP insertion.

    Args:
        circuit: Input quantum circuit.
        hardware_metric: Hardware distances and adjacency.
        initial_layout: Logical-to-physical initial assignment.

    Returns:
        A tuple of ``(routed_circuit, final_state)``.
    """
    state = RoutingState.from_initial_layout(initial_layout)
    routed = QuantumCircuit(circuit.num_qubits)

    for instruction in circuit.data:
        op = _instruction_operation(instruction)
        qargs = _instruction_qubits(instruction)
        logical = [circuit.find_bit(qubit).index for qubit in qargs]

        if len(logical) == 1:
            routed.append(op, [routed.qubits[state.physical_of(logical[0])]])
            continue

        if len(logical) != 2:
            routed.append(
                op, [routed.qubits[state.physical_of(q)] for q in logical]
            )
            continue

        logical_a, logical_b = logical
        physical_a = state.physical_of(logical_a)
        physical_b = state.physical_of(logical_b)

        while hardware_metric.hop_distances[physical_a][physical_b] > 1:
            path = _shortest_path(
                hardware_metric.adjacency, physical_a, physical_b
            )
            swap_left, swap_right = path[-2], path[-1]
            routed.swap(swap_left, swap_right)
            state.swap(swap_left, swap_right)
            physical_a = state.physical_of(logical_a)
            physical_b = state.physical_of(logical_b)

        routed.append(
            op,
            [
                routed.qubits[state.physical_of(logical_a)],
                routed.qubits[state.physical_of(logical_b)],
            ],
        )

    for logical in sorted(initial_layout):
        desired = initial_layout[logical]
        current = state.physical_of(logical)
        if current != desired:
            routed.swap(current, desired)
            state.swap(current, desired)

    return routed, state
