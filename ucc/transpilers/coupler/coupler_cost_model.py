"""Hardware-aware cost model for coupler-connected systems."""

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
from .coupler_architecture import CouplerConnectedArchitecture


@dataclass
class GateCosts:
    """Cost parameters for different gate types."""
    single_qubit: float = 1.0
    intra_chip_two_qubit: float = 10.0
    inter_chip_two_qubit: float = 100.0


class CouplerCostModel:
    """Cost model for hardware-aware compilation."""
    
    def __init__(self, architecture: CouplerConnectedArchitecture):
        self.architecture = architecture
        self.gate_costs = GateCosts()
    
    def compute_gate_cost(
        self, 
        chip_i: int, 
        chip_j: int, 
        gate_type: str = "cz"
    ) -> float:
        """Compute cost for a two-qubit gate between chips."""
        if chip_i == chip_j:
            # Intra-chip gate
            base_cost = self.gate_costs.intra_chip_two_qubit
            chip = self.architecture.chips[chip_i]
            return base_cost * (1 / chip.two_qubit_fidelity)
        else:
            # Inter-chip gate via coupler
            base_cost = self.gate_costs.inter_chip_two_qubit
            coupler_fidelity = self.architecture.get_coupler_fidelity(chip_i, chip_j)
            latency = self.architecture.get_coupler_latency(chip_i, chip_j)
            
            # Cost = latency * fidelity penalty
            return base_cost * (1 / coupler_fidelity) * (1 + latency / 1000)
    
    def compute_circuit_cost(self, routed_circuit) -> Dict[str, float]:
        """Compute total cost for a routed circuit.
        
        Args:
            routed_circuit: Dict with 'ops' list containing 
                          (chip_i, chip_j, gate_type) tuples
            
        Returns:
            Dict with total_cost, gate_count, latency
        """
        total_cost = 0.0
        gate_count = {'intra': 0, 'inter': 0}
        total_latency = 0.0
        
        for op in routed_circuit.get('ops', []):
            chip_i, chip_j, gate_type = op
            
            # Get latency
            if chip_i != chip_j:
                latency = self.architecture.get_coupler_latency(chip_i, chip_j)
                total_latency += latency
                gate_count['inter'] += 1
            else:
                gate_count['intra'] += 1
            
            # Add gate cost
            total_cost += self.compute_gate_cost(chip_i, chip_j, gate_type)
        
        return {
            'total_cost': total_cost,
            'gate_count': gate_count,
            'total_latency_ns': total_latency,
            'avg_gate_cost': total_cost / max(1, sum(gate_count.values())),
        }
    
    def fidelity_score(self, routed_circuit) -> float:
        """Compute effective fidelity of routed circuit."""
        total_fidelity = 1.0
        
        for op in routed_circuit.get('ops', []):
            chip_i, chip_j, _ = op
            
            if chip_i == chip_j:
                chip = self.architecture.chips[chip_i]
                total_fidelity *= chip.two_qubit_fidelity
            else:
                coupler_fid = self.architecture.get_coupler_fidelity(chip_i, chip_j)
                total_fidelity *= coupler_fid
        
        return total_fidelity


__all__ = ["CouplerCostModel", "GateCosts"]
