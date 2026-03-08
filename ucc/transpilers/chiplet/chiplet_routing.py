"""Chiplet-aware routing pass.

Routes quantum circuits on chiplet architectures, inserting SWAP gates
to enable inter-chiplet communication while optimizing for latency.
"""

from qiskit.dagcircuit import DAGCircuit
from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler import TranspilerError
from qiskit.transpiler.passes import LookaheadSwap, BasicSwap

from .chiplet_architecture import ChipletArchitecture


class ChipletRoutingPass:
    """Routes circuits on chiplet architectures with latency awareness.
    
    This pass inserts SWAP gates to enable communication between
    chiplets, optimizing for the higher latency of inter-chiplet links.
    """
    
    def __init__(self, architecture: ChipletArchitecture, 
                 optimization_level: int = 1):
        """Initialize chiplet routing pass.
        
        Args:
            architecture: Target chiplet architecture
            optimization_level: 0=basic, 1=lookahead, 2=optimized
        """
        self.architecture = architecture
        self.optimization_level = optimization_level
        
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run chiplet-aware routing.
        
        Args:
            dag: Input circuit DAG
            
        Returns:
            DAG with SWAP gates inserted for chiplet communication
        """
        # Extract current layout from DAG if available
        layout = getattr(dag, 'layout', None)
        
        if layout is None:
            raise TranspilerError(
                "ChipletRoutingPass requires a layout. "
                "Run ChipletPlacementPass first."
            )
        
        # Build coupling map from architecture
        coupling_map = self._build_coupling_map()
        
        # Choose routing strategy based on optimization level
        if self.optimization_level == 0:
            routed_dag = self._basic_routing(dag, coupling_map)
        else:
            routed_dag = self._lookahead_routing(dag, coupling_map)
            
        return routed_dag
    
    def _build_coupling_map(self) -> list:
        """Build coupling map from chiplet architecture.
        
        Returns:
            List of [control, target] pairs for allowed gates
        """
        couplings = []
        
        # Add intra-chiplet couplings
        for chiplet in self.architecture.chiplets:
            base = chiplet.id * 10
            for i in range(chiplet.num_qubits - 1):
                couplings.append([base + i, base + i + 1])
                
        # Add inter-chiplet couplings (links)
        for link in self.architecture.links:
            source_phys = link.source * 10
            target_phys = link.target * 10
            # Connect first qubit of each chiplet
            couplings.append([source_phys, target_phys])
            couplings.append([target_phys, source_phys])
            
        return couplings
    
    def _basic_routing(self, dag: DAGCircuit, 
                       coupling_map: list) -> DAGCircuit:
        """Basic SWAP insertion routing."""
        # Convert to Qiskit coupling map
        from qiskit.transpiler import CouplingMap
        cmap = CouplingMap(coupling_map)
        
        # Use BasicSwap for straightforward routing
        pass_ = BasicSwap(coupling_map=cmap)
        
        return pass_.run(dag)
    
    def _lookahead_routing(self, dag: DAGCircuit,
                           coupling_map: list) -> DAGCircuit:
        """Lookahead routing with optimization."""
        from qiskit.transpiler import CouplingMap
        cmap = CouplingMap(coupling_map)
        
        pass_ = LookaheadSwap(coupling_map=cmap, depth=2)
        
        return pass_.run(dag)
    
    def compute_latency_cost(self, dag: DAGCircuit) -> float:
        """Compute total latency cost of the routed circuit.
        
        Args:
            dag: Routed circuit DAG
            
        Returns:
            Total latency (lower is better)
        """
        layout = getattr(dag, 'layout', {})
        total_cost = 0.0
        
        for node in dag.gate_nodes():
            if len(node.qargs) == 2:
                q1, q2 = node.qargs
                p1 = layout.get(q1.index, q1.index)
                p2 = layout.get(q2.index, q2.index)
                
                # Get chiplets for each physical qubit
                c1 = self.architecture.get_qubit_to_chiplet(p1)
                c2 = self.architecture.get_qubit_to_chiplet(p2)
                
                # Add latency cost
                latency = self.architecture.get_inter_chiplet_latency(c1, c2)
                total_cost += latency
                
        return total_cost


__all__ = ["ChipletRoutingPass"]
