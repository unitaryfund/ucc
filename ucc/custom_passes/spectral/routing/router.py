"""SABRE-style router with a spectral swap-scoring prior."""

from __future__ import annotations

from collections import deque

from qiskit import QuantumCircuit
from qiskit.transpiler.layout import Layout

from ucc.custom_passes.spectral.hardware.hardware_metric import HardwareMetric
from ucc.custom_passes.spectral.routing.routing_state import RoutingState
from ucc.custom_passes.spectral.routing.swap_scoring import (
    DEFAULT_SPECTRAL_WEIGHT,
    spectral_tiebreak_score,
)


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


def _two_qubit_operations(
    circuit: QuantumCircuit,
) -> list[tuple[int, tuple[int, int]]]:
    """Return logical two-qubit gates with their circuit positions."""
    gates: list[tuple[int, tuple[int, int]]] = []
    for index, instruction in enumerate(circuit.data):
        qargs = _instruction_qubits(instruction)
        if len(qargs) != 2:
            continue
        logical = tuple(
            sorted(circuit.find_bit(qubit).index for qubit in qargs)
        )
        gates.append((index, logical))
    return gates


def _candidate_swaps(
    metric: HardwareMetric, physical_a: int, physical_b: int
) -> list[tuple[int, int]]:
    """Return local SWAP candidates around the active front gate."""
    candidates: set[tuple[int, int]] = set()
    for origin in (physical_a, physical_b):
        for neighbor in metric.adjacency.get(origin, {}):
            if neighbor == origin:
                continue
            candidates.add(tuple(sorted((origin, neighbor))))
    return sorted(candidates)


def _append_instruction(
    routed: QuantumCircuit,
    state: RoutingState,
    instruction,
    circuit: QuantumCircuit,
) -> None:
    """Append a single instruction to the routed circuit under the current map."""
    op = _instruction_operation(instruction)
    qargs = _instruction_qubits(instruction)
    logical = [circuit.find_bit(qubit).index for qubit in qargs]
    routed.append(
        op,
        [
            routed.qubits[state.physical_of(logical_qubit)]
            for logical_qubit in logical
        ],
    )


def route(
    circuit: QuantumCircuit,
    hardware_metric: HardwareMetric,
    initial_layout,
    *,
    spectral_weight: float = DEFAULT_SPECTRAL_WEIGHT,
):
    """Route a circuit onto the hardware graph with SWAP insertion.

    Args:
        circuit: Input quantum circuit.
        hardware_metric: Hardware distances and adjacency.
        initial_layout: Logical-to-physical initial assignment.
        spectral_weight: Weight applied to the spectral-alignment term when
            scoring candidate SWAPs (see ``swap_scoring.spectral_tiebreak_score``).
            Set to ``0.0`` to recover plain SABRE-style routing.

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

    two_qubit_gates = _two_qubit_operations(circuit)
    gate_index = 0

    for instruction in circuit.data:
        qargs = _instruction_qubits(instruction)
        logical = [circuit.find_bit(qubit).index for qubit in qargs]

        if len(logical) == 1:
            _append_instruction(routed, state, instruction, circuit)
            continue

        if len(logical) != 2:
            _append_instruction(routed, state, instruction, circuit)
            continue

        logical_a, logical_b = logical
        physical_a = state.physical_of(logical_a)
        physical_b = state.physical_of(logical_b)

        current_gate = tuple(sorted((logical_a, logical_b)))
        front_layer = [current_gate]
        for _, gate in two_qubit_gates[gate_index + 1 : gate_index + 3]:
            front_layer.append(gate)
        state.front_layer = front_layer

        while hardware_metric.hop_distances[physical_a][physical_b] > 1:
            candidates = _candidate_swaps(
                metric=hardware_metric,
                physical_a=physical_a,
                physical_b=physical_b,
            )
            if not candidates:
                path = _shortest_path(
                    hardware_metric.adjacency, physical_a, physical_b
                )
                candidates = [tuple(sorted((path[-2], path[-1])))]

            swap_left, swap_right = min(
                candidates,
                key=lambda swap: spectral_tiebreak_score(
                    state,
                    hardware_metric,
                    swap[0],
                    swap[1],
                    lookahead_depth=len(front_layer),
                    spectral_weight=spectral_weight,
                ),
            )
            routed.swap(swap_left, swap_right)
            state.swap(swap_left, swap_right)
            physical_a = state.physical_of(logical_a)
            physical_b = state.physical_of(logical_b)

        _append_instruction(routed, state, instruction, circuit)
        gate_index += 1

    for logical in sorted(initial_mapping):
        desired = initial_mapping[logical]
        current = state.physical_of(logical)
        if current != desired:
            routed.swap(current, desired)
            state.swap(current, desired)

    return routed, state
