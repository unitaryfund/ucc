"""Coupler-connected quantum architecture model.

Models quantum computing architectures where chiplets are connected
via coherent coupler links, as described in arXiv:2502.08997.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import numpy as np


@dataclass
class CouplerSpec:
    """Specification for a coherent coupler."""
    frequency: float  # GHz
    coherence_time: float  # microseconds
    gate_fidelity: float
    gate_latency: float  # nanoseconds
    max_coupling_strength: float  # MHz
    temperature: float  # millikelvin


@dataclass 
class ChipSpec:
    """Specification for a quantum chip/chiplet."""
    num_qubits: int
    coherence_time: float  # microseconds
    single_qubit_fidelity: float
    two_qubit_fidelity: float
    gate_latency: float  # nanometers
    topology: str = "grid"  # grid, heavy-hex, etc.


@dataclass
class CouplerLink:
    """Represents a coupler link between two chiplets."""
    source_chip: int
    target_chip: int
    coupler: CouplerSpec
    distance: float  # millimeters
    loss: float  # dB


class CouplerConnectedArchitecture:
    """Architecture model for coupler-connected modular quantum systems."""
    
    def __init__(
        self,
        chips: List[ChipSpec],
        couplers: List[CouplerSpec],
        links: List[CouplerLink],
    ):
        self.chips = chips
        self.couplers = couplers
        self.links = links
        self._build_adjacency_matrix()
    
    def _build_adjacency_matrix(self):
        """Build adjacency matrix for chip connectivity."""
        n = len(self.chips)
        self.adjacency = np.zeros((n, n))
        self.link_props = {}
        
        for link in self.links:
            self.adjacency[link.source_chip, link.target_chip] = 1
            self.adjacency[link.target_chip, link.source_chip] = 1
            key = (link.source_chip, link.target_chip)
            self.link_props[key] = {
                'coupler': link.coupler,
                'distance': link.distance,
                'loss': link.loss,
            }
    
    def get_coupler_fidelity(self, chip_i: int, chip_j: int) -> float:
        """Get effective two-qubit fidelity across coupler."""
        if (chip_i, chip_j) in self.link_props:
            return self.link_props[(chip_i, chip_j)]['coupler'].gate_fidelity
        return 0.0
    
    def get_coupler_latency(self, chip_i: int, chip_j: int) -> float:
        """Get gate latency across coupler (ns)."""
        if (chip_i, chip_j) in self.link_props:
            base = self.link_props[(chip_i, chip_j)]['coupler'].gate_latency
            distance = self.link_props[(chip_i, chip_j)]['distance']
            # Add propagation delay (speed of light in coax ~ 2/3 c)
            prop_delay = distance * 5  # ns/mm
            return base + prop_delay
        return float('inf')
    
    @classmethod
    def from_config(cls, config: Dict):
        """Create architecture from configuration dict."""
        chips = [ChipSpec(**c) for c in config['chips']]
        couplers = [CouplerSpec(**c) for c in config['couplers']]
        
        links = []
        for link_cfg in config.get('links', []):
            coupler_idx = link_cfg['coupler_idx']
            links.append(CouplerLink(
                source_chip=link_cfg['source'],
                target_chip=link_cfg['target'],
                coupler=couplers[coupler_idx],
                distance=link_cfg['distance'],
                loss=link_cfg.get('loss', 0),
            ))
        
        return cls(chips, couplers, links)
    
    def summary(self) -> str:
        """Return architecture summary."""
        total_qubits = sum(c.num_qubits for c in self.chips)
        return f"Coupler-connected: {len(self.chips)} chips, {total_qubits} total qubits, {len(self.links)} coupler links"
