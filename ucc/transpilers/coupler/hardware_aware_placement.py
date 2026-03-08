"""Hardware-aware placement pass for coupler-connected systems."""

from typing import Dict, List, Set
from collections import defaultdict
import numpy as np
from qiskit.transpiler import PassManager, Layout
from qiskit.transpiler.passes import BasicLayout
from qiskit.dagcircuit import DAGCircuit
from qiskit.converters import circuit_to_dag

from .coupler_architecture import CouplerConnectedArchitecture
from .coupler_cost_model import CouplerCostModel


class HardwareAwarePlacementPass:
    """Placement pass optimized for coupler-connected hardware."""
    
    def __init__(
        self,
        architecture: CouplerConnectedArchitecture,
        cost_model: CouplerCostModel,
    ):
        self.architecture = architecture
        self.cost_model = cost_model
    
    def run(self, dag: DAGCircuit) -> Layout:
        """Run hardware-aware placement.
        
        Analyzes circuit dependencies and places qubits to minimize
        inter-chip gate overhead.
        """
        # Build interaction graph
        interaction_graph = self._build_interaction_graph(dag)
        
        # Partition into chiplets
        partitions = self._partition_circuit(interaction_graph)
        
        # Map partitions to chips
        layout = self._map_partitions_to_chips(partitions, dag)
        
        return layout
    
    def _build_interaction_graph(self, dag: DAGCircuit) -> Dict[int, List[int]]:
        """Build weighted graph of qubit interactions."""
        interactions = defaultdict(lambda: defaultdict(int))
        
        for node in dag.gate_nodes():
            if len(node.qargs) == 2:
                q1 = dag.qargs.index(node.qargs[0])
                q2 = dag.qargs.index(node.qargs[1])
                interactions[q1][q2] += 1
                interactions[q2][q1] += 1
        
        return dict(interactions)
    
    def _partition_circuit(
        self, 
        interactions: Dict[int, Dict[int, int]]
    ) -> List[Set[int]]:
        """Partition qubits into groups based on interactions."""
        # Greedy partition: assign qubits to chips to minimize inter-chip gates
        partitions = [set() for _ in self.architecture.chips]
        qubit_chips = {}
        
        # Start with most connected qubit
        if not interactions:
            return [set(range(len(interactions)))] if interactions else [set()]
        
        sorted_qubits = sorted(
            interactions.keys(),
            key=lambda q: sum(interactions[q].values()),
            reverse=True
        )
        
        for qubit in sorted_qubits:
            if qubit in qubit_chips:
                continue
                
            # Find chip with most interactions
            best_chip = 0
            best_score = -1
            
            for chip_idx, partition in enumerate(partitions):
                score = 0
                for other_qubit in partition:
                    if other_qubit in interactions.get(qubit, {}):
                        score += interactions[qubit][other_qubit]
                
                if score > best_score:
                    best_score = score
                    best_chip = chip_idx
            
            partitions[best_chip].add(qubit)
            qubit_chips[qubit] = best_chip
        
        return [p for p in partitions if p]
    
    def _map_partitions_to_chips(
        self,
        partitions: List[Set[int]],
        dag: DAGCircuit
    ) -> Layout:
        """Map qubit partitions to physical chips."""
        layout = Layout()
        
        qubit_idx = 0
        for chip_idx, partition in enumerate(partitions):
            chip = self.architecture.chips[chip_idx]
            
            for local_qubit in range(len(partition)):
                if qubit_idx < dag.num_qubits():
                    # Map logical qubit to physical (chip, local_qubit)
                    layout[dag.qargs[qubit_idx]] = (chip_idx, local_qubit)
                    qubit_idx += 1
        
        return layout


__all__ = ["HardwareAwarePlacementPass"]
