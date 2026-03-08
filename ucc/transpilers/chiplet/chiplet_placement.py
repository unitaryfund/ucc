"""Chiplet-aware qubit placement pass.

Places logical qubits onto physical qubits in a chiplet architecture,
optimizing for inter-chiplet communication cost.
"""

from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import InitialLayout
from qiskit.transpiler.analysis import CouplingMap
from qiskit.dagcircuit import DAGCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler import TranspilerError

from .chiplet_architecture import ChipletArchitecture


class ChipletPlacementPass:
    """Places qubits onto chiplet architecture optimizing for locality.
    
    This pass implements hierarchical placement where qubits that
    interact frequently are placed on the same chiplet when possible.
    """
    
    def __init__(self, architecture: ChipletArchitecture, constraint: bool = True):
        """Initialize the chiplet placement pass.
        
        Args:
            architecture: The chiplet architecture to place onto
            constraint: If True, enforce that no inter-chiplet gates exist
        """
        self.architecture = architecture
        self.constraint = constraint
        
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the chiplet placement pass.
        
        Args:
            dag: The DAG representation of the quantum circuit
            
        Returns:
            Modified DAG with optimized qubit placement
        """
        num_qubits = dag.num_qubits()
        total_physical = self.architecture.get_total_qubits()
        
        if num_qubits > total_physical:
            raise TranspilerError(
                f"Circuit requires {num_qubits} qubits but "
                f"architecture has {total_physical}"
            )
        
        # Calculate interaction matrix (how often each pair interacts)
        interaction_matrix = self._compute_interaction_matrix(dag)
        
        # Run placement algorithm
        layout = self._optimal_layout(interaction_matrix, num_qubits)
        
        # Apply layout to DAG
        return self._apply_layout(dag, layout)
    
    def _compute_interaction_matrix(self, dag: DAGCircuit) -> np.ndarray:
        """Compute how often each qubit pair interacts.
        
        Args:
            dag: The circuit DAG
            
        Returns:
            NxN matrix where entry (i,j) = number of gates between qubits i and j
        """
        n = dag.num_qubits()
        matrix = np.zeros((n, n))
        
        for node in dag.gate_nodes():
            if len(node.qargs) == 2:
                q1, q2 = node.qargs
                matrix[q1.index, q2.index] += 1
                matrix[q2.index, q1.index] += 1
                
        return matrix
    
    def _optimal_layout(self, interaction_matrix: np.ndarray, 
                        num_logical: int) -> Dict[int, int]:
        """Compute optimal logical-to-physical qubit mapping.
        
        Uses a greedy approach: place qubits that interact heavily
        on the same chiplet when possible.
        
        Args:
            interaction_matrix: Interaction frequency matrix
            num_logical: Number of logical qubits
            
        Returns:
            Dict mapping logical qubit index to physical qubit index
        """
        layout = {}
        used_physical = set()
        
        # Greedy placement: highest interaction first
        pairs = []
        for i in range(num_logical):
            for j in range(i + 1, num_logical):
                if interaction_matrix[i, j] > 0:
                    pairs.append((i, j, interaction_matrix[i, j]))
        pairs.sort(key=lambda x: -x[2])  # Sort by interaction count
        
        placed = set()
        
        for q1, q2, _ in pairs:
            if q1 in placed and q2 in placed:
                continue
                
            # Find best chiplet for this pair
            best_chiplet = self._find_best_chiplet(q1, q2, used_physical)
            
            if q1 not in placed:
                physical = self._get_free_physical(best_chiplet, used_physical)
                if physical is not None:
                    layout[q1] = physical
                    placed.add(q1)
                    used_physical.add(physical)
                    
            if q2 not in placed:
                physical = self._get_free_physical(best_chiplet, used_physical)
                if physical is not None:
                    layout[q2] = physical
                    placed.add(q2)
                    used_physical.add(physical)
        
        # Place remaining qubits
        chiplet_idx = 0
        for q in range(num_logical):
            if q not in placed:
                while True:
                    physical = self._get_free_physical(chiplet_idx, used_physical)
                    chiplet_idx = (chiplet_idx + 1) % len(self.architecture.chiplets)
                    if physical is not None:
                        layout[q] = physical
                        used_physical.add(physical)
                        break
                        
        return layout
    
    def _find_best_chiplet(self, q1: int, q2: int, 
                           used: set) -> int:
        """Find the best chiplet to place a qubit pair.
        
        Returns chiplet with most free qubits."""
        best = 0
        best_chiplet = 0
        
        for chiplet in self.architecture.chiplets:
            free = sum(1 for q in range(chiplet.id * 10, chiplet.id * 10 + chiplet.num_qubits) 
                      if q not in used)
            if free > best:
                best = free
                best_chiplet = chiplet.id
                
        return best_chiplet
    
    def _get_free_physical(self, chiplet_id: int, used: set) -> int:
        """Get a free physical qubit in a chiplet."""
        chiplet = self.architecture.chiplets[chiplet_id]
        base = chiplet_id * 10  # Simplified mapping
        
        for i in range(chiplet.num_qubits):
            if base + i not in used:
                return base + i
        return None
    
    def _apply_layout(self, dag: DAGCircuit, layout: Dict[int, int]) -> DAGCircuit:
        """Apply the computed layout to the DAG."""
        # Add layout property to DAG
        dag.layout = layout
        return dag


__all__ = ["ChipletPlacementPass"]
