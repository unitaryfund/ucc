"""CCMap: Hardware-aware Compilation for Chip-to-Chip Coupler-Connected Modular Quantum Systems

Based on: https://arxiv.org/pdf/2505.09036

This pass implements:
- Circuit partitioning for multi-chip systems
- Coupler-aligned cost metric calculation  
- Global mapping to minimize compilation cost
- Integration with calibration data

Author: eyerahnik
Bounty: #536
"""

from .ccmap_pass import CCMapPass
from .partition import partition_circuit
from .cost_metric import CouplerCostMetric
from .global_map import global_mapping

__all__ = [
    "CCMapPass",
    "partition_circuit", 
    "CouplerCostMetric",
    "global_mapping"
]

__version__ = "0.1.0"
