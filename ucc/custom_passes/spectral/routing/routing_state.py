"""Mutable routing state: current logical-to-physical mapping and front layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RoutingState:
    """Track the current logical-to-physical assignment during routing."""

    logical_to_physical: dict[int, int]
    physical_to_logical: dict[int, int] = field(init=False)
    front_layer: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.physical_to_logical = {
            physical: logical
            for logical, physical in self.logical_to_physical.items()
        }

    @classmethod
    def from_initial_layout(
        cls,
        initial_layout: dict[int, int],
        *,
        front_layer: list[tuple[int, int]] | None = None,
    ) -> "RoutingState":
        return cls(
            logical_to_physical=dict(initial_layout),
            front_layer=list(front_layer or []),
        )

    def swap(self, physical_a: int, physical_b: int) -> None:
        """Swap the logical qubits currently occupying two physical qubits."""
        logical_a = self.physical_to_logical[physical_a]
        logical_b = self.physical_to_logical[physical_b]

        self.logical_to_physical[logical_a] = physical_b
        self.logical_to_physical[logical_b] = physical_a
        self.physical_to_logical[physical_a] = logical_b
        self.physical_to_logical[physical_b] = logical_a

    def physical_of(self, logical: int) -> int:
        return self.logical_to_physical[logical]

    def logical_of(self, physical: int) -> int:
        return self.physical_to_logical[physical]

    def remove_front_gate(self, gate: tuple[int, int]) -> None:
        try:
            self.front_layer.remove(gate)
        except ValueError:
            pass
