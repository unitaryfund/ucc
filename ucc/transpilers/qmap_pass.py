"""
QMAP Routing Pass for UCC
=========================

Integrates MQT QMAP for quantum circuit mapping and routing.

QMAP provides:
- Exact mapping (SAT/SMT-based, gate-optimal)
- Heuristic mapping (A*-search, scalable)
- Clifford circuit optimization
- Neutral atom compilation

Installation:
    pip install mqt.qmap

References:
    - Paper: https://arxiv.org/abs/2506.13720v1
    - Repo: https://github.com/munich-quantum-toolkit/qmap
    - Docs: https://mqt.readthedocs.io/projects/qmap
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler import PassManager
from qiskit import QuantumCircuit
from qiskit.providers.fake_provider import GenericBackendV2

if TYPE_CHECKING:
    from qiskit.dagcircuit import DAGCircuit

try:
    from mqt.qmap.plugins.qiskit.sc import compile_ as qmap_compile
    from mqt.qmap.plugins.qiskit.clifford_synthesis import optimize_clifford
    QMAP_AVAILABLE = True
except ImportError:
    QMAP_AVAILABLE = False


class QMAPRoutingPass(TransformationPass):
    """UCC transpiler pass using MQT QMAP for routing and mapping.
    
    QMAP provides both exact (SAT-based) and heuristic (A*-search)
    mapping algorithms for routing quantum circuits to hardware.
    
    Args:
        method: "exact" for gate-optimal SAT-based mapping,
                "heuristic" for scalable A*-search mapping
        use_teleportation: Enable quantum teleportation for routing
        verbose: Print detailed mapping statistics
    
    Examples:
        >>> from ucc import compile
        >>> from ucc.transpilers.qmap_pass import QMAPRoutingPass
        >>> 
        >>> # Use QMAP for routing
        >>> compiled = compile(
        ...     circuit,
        ...     custom_passes=[QMAPRoutingPass(method="heuristic")]
        ... )
    """
    
    def __init__(
        self,
        method: str = "heuristic",
        use_teleportation: bool = False,
        verbose: bool = False,
    ):
        if not QMAP_AVAILABLE:
            raise ImportError(
                "QMAP not installed. Install with: pip install mqt.qmap"
            )
        
        super().__init__()
        self.method = method
        self.use_teleportation = use_teleportation
        self.verbose = verbose
    
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run QMAP routing on the circuit."""
        # Convert DAG to circuit
        circuit = dag.to_circuit()
        
        # Create a generic backend for mapping
        # In production, this would use the actual target backend
        num_qubits = circuit.num_qubits
        backend = GenericBackendV2(
            num_qubits=num_qubits,
            coupling_map=self._generate_coupling_map(num_qubits),
        )
        
        # Map and route using QMAP
        from mqt.qmap.sc import Method
        method_enum = Method.heuristic if self.method == "heuristic" else Method.exact
        mapped_circuit, results = qmap_compile(
            circuit,
            arch=backend,
            method=method_enum,
        )
        
        if self.verbose:
            print(f"QMAP Routing Results:")
            print(f"  Method: {self.method}")
            print(f"  Initial gates: {circuit.num_nonlocal_gates()}")
            print(f"  Final gates: {mapped_circuit.num_nonlocal_gates()}")
            print(f"  Mapping time: {results.mapping_time:.4f}s")
            if hasattr(results, 'swaps'):
                print(f"  SWAPs added: {results.swaps}")
        
        # Convert back to DAG
        from qiskit.converters import circuit_to_dag
        return circuit_to_dag(mapped_circuit)
    
    def _generate_coupling_map(self, n: int) -> list[list[int]]:
        """Generate a linear coupling map for n qubits."""
        coupling_map = []
        for i in range(n - 1):
            coupling_map.extend([[i, i + 1], [i + 1, i]])
        return coupling_map


class QMAPCliffordPass(TransformationPass):
    """UCC transpiler pass for Clifford circuit optimization.
    
    Uses QMAP's SAT-based Clifford synthesis for depth/gate-optimal
    optimization of Clifford circuits.
    
    Examples:
        >>> from ucc import compile
        >>> from ucc.transpilers.qmap_pass import QMAPCliffordPass
        >>> 
        >>> compiled = compile(
        ...     clifford_circuit,
        ...     custom_passes=[QMAPCliffordPass()]
        ... )
    """
    
    def __init__(self, verbose: bool = False):
        if not QMAP_AVAILABLE:
            raise ImportError(
                "QMAP not installed. Install with: pip install mqt.qmap"
            )
        
        super().__init__()
        self.verbose = verbose
    
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run Clifford optimization on the circuit."""
        circuit = dag.to_circuit()
        
        # Optimize using QMAP's Clifford synthesis
        optimized, results = optimize_clifford(circuit)
        
        if self.verbose:
            print(f"QMAP Clifford Optimization Results:")
            print(f"  Initial depth: {circuit.depth()}")
            print(f"  Final depth: {optimized.depth()}")
            print(f"  Initial gates: {len(circuit)}")
            print(f"  Final gates: {len(optimized)}")
        
        from qiskit.converters import circuit_to_dag
        return circuit_to_dag(optimized)


def create_qmap_pass_manager(
    method: str = "heuristic",
    optimize_cliffords: bool = True,
) -> PassManager:
    """Create a pass manager with QMAP passes.
    
    Args:
        method: "exact" or "heuristic" for routing
        optimize_cliffords: Whether to include Clifford optimization
    
    Returns:
        PassManager configured with QMAP passes
    """
    passes = []
    
    if optimize_cliffords:
        passes.append(QMAPCliffordPass())
    
    passes.append(QMAPRoutingPass(method=method))
    
    return PassManager(passes)


__all__ = [
    "QMAPRoutingPass",
    "QMAPCliffordPass",
    "create_qmap_pass_manager",
    "QMAP_AVAILABLE",
]
