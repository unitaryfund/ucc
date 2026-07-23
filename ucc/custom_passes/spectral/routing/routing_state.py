"""Mutable routing state: current logical-to-physical mapping and front layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RoutingState:
    """Track the current logical-to-physical assignment during routing."""

    logical_to_physical: dict[int, int]
    reference_layout: dict[int, int] = field(default_factory=dict)
    physical_to_logical: dict[int, int] = field(init=False)
    front_layer: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Build the inverse physical-to-logical map."""
        if not self.reference_layout:
            self.reference_layout = dict(self.logical_to_physical)
        self.physical_to_logical = {
            physical: logical
            for logical, physical in self.logical_to_physical.items()
        }

    @classmethod
    def from_initial_layout(
        cls,
        initial_layout: dict[int, int],
        *,
        reference_layout: dict[int, int] | None = None,
        front_layer: list[tuple[int, int]] | None = None,
    ) -> "RoutingState":
        """Create a routing state from an initial layout and optional front layer."""
        return cls(
            logical_to_physical=dict(initial_layout),
            reference_layout=dict(reference_layout or initial_layout),
            front_layer=list(front_layer or []),
        )

    def swap(self, physical_a: int, physical_b: int) -> None:
        """Swap the logical qubits currently occupying two physical qubits.

        Args:
            physical_a: First physical qubit index.
            physical_b: Second physical qubit index.
        """
        logical_a = self.physical_to_logical.get(physical_a)
        logical_b = self.physical_to_logical.get(physical_b)

        if logical_a is None and logical_b is None:
            return
        if logical_a is None:
            self.logical_to_physical[logical_b] = physical_a
            self.physical_to_logical[physical_a] = logical_b
            self.physical_to_logical.pop(physical_b, None)
            return
        if logical_b is None:
            self.logical_to_physical[logical_a] = physical_b
            self.physical_to_logical[physical_b] = logical_a
            self.physical_to_logical.pop(physical_a, None)
            return

        self.logical_to_physical[logical_a] = physical_b
        self.logical_to_physical[logical_b] = physical_a
        self.physical_to_logical[physical_a] = logical_b
        self.physical_to_logical[physical_b] = logical_a

    def physical_of(self, logical: int) -> int:
        """Return the current physical qubit for a logical qubit."""
        return self.logical_to_physical[logical]

    def logical_of(self, physical: int) -> int:
        """Return the logical qubit currently occupying a physical qubit."""
        return self.physical_to_logical[physical]

    def remove_front_gate(self, gate: tuple[int, int]) -> None:
        """Remove a gate from the front layer if it is present."""
        try:
            self.front_layer.remove(gate)
        except ValueError:
            pass
