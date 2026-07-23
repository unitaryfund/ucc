"""Pure interaction-sequence router producing a SWAP-inserted circuit."""

from __future__ import annotations

from collections import deque

from qiskit import QuantumCircuit
from qiskit.transpiler.layout import Layout

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


def _layout_to_initial_mapping(
    circuit: QuantumCircuit,
    layout,
) -> dict[int, int]:
    """Normalize a Qiskit layout or mapping to logical-to-physical integers."""
    if isinstance(layout, dict):
        return dict(layout)

    if isinstance(layout, Layout):
        return {
            circuit.find_bit(virtual_bit).index: physical
            for virtual_bit, physical in layout.get_virtual_bits().items()
        }

    if hasattr(layout, "get_virtual_bits"):
        return {
            circuit.find_bit(virtual_bit).index: physical
            for virtual_bit, physical in layout.get_virtual_bits().items()
        }

    raise TypeError("initial_layout must be a mapping or Qiskit Layout")


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
    initial_layout,
):
    """Route a circuit onto the hardware graph with SWAP insertion.

    Args:
        circuit: Input quantum circuit.
        hardware_metric: Hardware distances and adjacency.
        initial_layout: Logical-to-physical initial assignment.

    Returns:
        A tuple of ``(routed_circuit, final_state)``.
    """
    initial_mapping = _layout_to_initial_mapping(circuit, initial_layout)
    state = RoutingState.from_initial_layout(initial_mapping)
    num_physical_qubits = max(
        max(hardware_metric.adjacency) + 1 if hardware_metric.adjacency else 0,
        max(initial_mapping.values()) + 1 if initial_mapping else 0,
    )
    routed = QuantumCircuit(num_physical_qubits or circuit.num_qubits)

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

    for logical in sorted(initial_mapping):
        desired = initial_mapping[logical]
        current = state.physical_of(logical)
        if current != desired:
            routed.swap(current, desired)
            state.swap(current, desired)

    return routed, state
