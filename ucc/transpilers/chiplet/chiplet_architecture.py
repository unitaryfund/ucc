"""Chiplet Architecture representation for modular quantum systems.

This module provides classes to represent chiplet-based quantum computing
architectures where multiple small quantum chips are connected via
quantum links.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import numpy as np


@dataclass
class Chiplet:
    """Represents a single chiplet (quantum chip) in the architecture.
    
    Attributes:
        id: Unique identifier for this chiplet
        num_qubits: Number of physical qubits in this chiplet
        fidelity: Average gate fidelity for this chiplet
    """
    id: int
    num_qubits: int
    fidelity: float = 0.99


@dataclass 
class ChipletLink:
    """Represents a quantum link between two chiplets.
    
    Attributes:
        source: Source chiplet ID
        target: Target chiplet ID
        latency: Gate latency factor (1.0 = same as on-chip)
        fidelity: Link transmission fidelity
    """
    source: int
    target: int
    latency: float = 10.0  # Inter-chiplet gates are typically slower
    fidelity: float = 0.95


@dataclass
class ChipletArchitecture:
    """Represents a complete chiplet-based quantum architecture.
    
    This models a modular quantum computer composed of multiple
    interconnected chiplets, as described in the SEQC paper.
    
    Attributes:
        chiplets: List of chiplets in the architecture
        links: List of quantum links between chiplets
        name: Optional name for the architecture
    """
    chiplets: List[Chiplet] = field(default_factory=list)
    links: List[ChipletLink] = field(default_factory=list)
    name: str = "chiplet_architecture"
    
    @classmethod
    def from_grid(cls, rows: int, cols: int, qubits_per_chiplet: int = 10, 
                  intra_latency: float = 1.0, inter_latency: float = 10.0,
                  intra_fidelity: float = 0.99, inter_fidelity: float = 0.95) -> "ChipletArchitecture":
        """Create a grid of chiplets.
        
        Args:
            rows: Number of rows in the grid
            cols: Number of columns in the grid  
            qubits_per_chiplet: Number of qubits per chiplet
            intra_latency: Gate latency within a chiplet
            inter_latency: Gate latency between chiplets
            intra_fidelity: Gate fidelity within a chiplet
            inter_fidelity: Link fidelity between chiplets
            
        Returns:
            ChipletArchitecture with grid topology
        """
        chiplets = []
        links = []
        chiplet_id = 0
        
        for row in range(rows):
            for col in range(cols):
                chiplets.append(Chiplet(
                    id=chiplet_id,
                    num_qubits=qubits_per_chiplet,
                    fidelity=intra_fidelity
                ))
                
                # Connect to neighbors (right and down)
                if col > 0:  # Connect to left
                    links.append(ChipletLink(
                        source=chiplet_id - 1,
                        target=chiplet_id,
                        latency=inter_latency,
                        fidelity=inter_fidelity
                    ))
                if row > 0:  # Connect to above
                    links.append(ChipletLink(
                        source=chiplet_id - cols,
                        target=chiplet_id,
                        latency=inter_latency,
                        fidelity=inter_fidelity
                    ))
                    
                chiplet_id += 1
                
        return cls(chiplets=chiplets, links=links, name=f"{rows}x{cols}_chiplet_grid")
    
    def get_total_qubits(self) -> int:
        """Get total number of qubits across all chiplets."""
        return sum(c.num_qubits for c in self.chiplets)
    
    def get_inter_chiplet_latency(self, chiplet1: int, chiplet2: int) -> float:
        """Get latency between two chiplets.
        
        Args:
            chiplet1: First chiplet ID
            chiplet2: Second chiplet ID
            
        Returns:
            Latency factor (1.0 if same chiplet, for inter-chi higherplet)
        """
        if chiplet1 == chiplet2:
            return 1.0
            
        for link in self.links:
            if (link.source == chiplet1 and link.target == chiplet2) or \
               (link.source == chiplet2 and link.target == chiplet1):
                return link.latency
        return float('inf')  # No connection
    
    def get_qubit_to_chiplet(self, qubit_id: int) -> int:
        """Map a physical qubit ID to its chiplet.
        
        Args:
            qubit_id: Global physical qubit ID
            
        Returns:
            Chiplet ID containing this qubit
        """
        running = 0
        for chiplet in self.chiplets:
            if qubit_id < running + chiplet.num_qubits:
                return chiplet.id
            running += chiplet.num_qubits
        raise ValueError(f"Qubit {qubit_id} not found in architecture")


__all__ = ["ChipletArchitecture", "Chiplet", "ChipletLink"]
