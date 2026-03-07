"""
OPTRAN: Optimal Pass Selection for Quantum Transpilation
=========================================================

Automatically selects the optimal combination of transpiler passes
based on circuit characteristics and target hardware.

Reference: https://arxiv.org/abs/2306.15020
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np

from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import (
    Optimize1qGates,
    CXCancellation,
    Collect2qBlocks,
    ConsolidateBlocks,
    RemoveBarriers,
    RemoveResetInZeroState,
    Depth,
    Size,
    CountOps,
)
from qiskit import QuantumCircuit
from qiskit.circuit.library import CliffOrdCircuit

from qiskit.quantum_info import Clifford


@dataclass
class PassConfig:
    """Configuration for a transpiler pass."""
    name: str
    pass_class: type
    params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


# Predefined pass configurations
PASS_CONFIGS = [
    PassConfig("optimize_1q", Optimize1qGates),
    PassConfig("cx_cancel", CXCancellation),
    PassConfig("collect_2q", Collect2qBlocks),
    PassConfig("consolidate", ConsolidateBlocks),
    PassConfig("remove_barriers", RemoveBarriers),
    PassConfig("remove_reset", RemoveResetInZeroState),
]

# Pass sequences that work well together
PASS_SEQUENCES = {
    "light": ["optimize_1q", "cx_cancel"],
    "medium": ["optimize_1q", "cx_cancel", "collect_2q"],
    "heavy": ["optimize_1q", "cx_cancel", "collect_2q", "consolidate"],
    "clifford": ["optimize_1q", "cx_cancel", "collect_2q", "consolidate"],
}


class CircuitFeatures:
    """Extract features from a quantum circuit for pass selection."""
    
    @staticmethod
    def extract(circuit: QuantumCircuit) -> Dict[str, float]:
        """
        Extract relevant features from circuit.
        
        Args:
            circuit: Input quantum circuit
            
        Returns:
            Dictionary of features
        """
        ops = circuit.count_ops()
        
        features = {
            "num_qubits": circuit.num_qubits,
            "depth": circuit.depth(),
            "size": circuit.size(),
            "num_2q_gates": ops.get("cx", 0) + ops.get("cz", 0) + ops.get("ecr", 0),
            "num_1q_gates": ops.get("rx", 0) + ops.get("ry", 0) + ops.get("rz", 0) + ops.get("h", 0),
            "barrier_count": ops.get("barrier", 0),
            "measure_count": ops.get("measure", 0),
            "clifford_ratio": CircuitFeatures._clifford_ratio(circuit),
        }
        
        return features
    
    @staticmethod
    def _clifford_ratio(circuit: QuantumCircuit) -> float:
        """Calculate ratio of Clifford gates."""
        ops = circuit.count_ops()
        clifford_gates = {"h", "s", "sdg", "x", "y", "z", "cx", "cy", "cz", "swap"}
        
        total = sum(ops.values())
        if total == 0:
            return 1.0
            
        clifford_count = sum(ops.get(g, 0) for g in clifford_gates)
        return clifford_count / total


class OPTRANPass(TransformationPass):
    """
    OPTRAN: Optimal Pass Selection for Quantum Transpilation
    
    Automatically selects the best combination of transpiler passes
    based on circuit characteristics using Clifford-based benchmarking.
    
    The key insight is that Clifford circuits can be efficiently simulated
    classically, so we can test different pass combinations on Clifford
    approximations of the target circuit to find the optimal set.
    
    Example:
        >>> from ucc.transpilers.optran_pass import OPTRANPass
        >>> from qiskit import QuantumCircuit
        >>> 
        >>> # Create circuit
        >>> qc = QuantumCircuit(10)
        >>> # ... add gates ...
        >>> 
        >>> # Auto-select optimal passes
        >>> optran = OPTRANPass(target_backend=backend)
        >>> optimized = optran(qc)
    """
    
    def __init__(
        self,
        target_backend=None,
        optimization_level: int = 2,
        benchmark_samples: int = 5,
        pass_sequences: Optional[Dict[str, List[str]]] = None,
    ):
        """
        Initialize OPTRAN pass selector.
        
        Args:
            target_backend: Target quantum backend
            optimization_level: Optimization level (0-3)
            benchmark_samples: Number of Clifford samples for benchmarking
            pass_sequences: Custom pass sequences to evaluate
        """
        super().__init__()
        self.target_backend = target_backend
        self.optimization_level = optimization_level
        self.benchmark_samples = benchmark_samples
        self.pass_sequences = pass_sequences or PASS_SEQUENCES
        self._best_sequence = None
        
    def _generate_clifford_approximation(
        self, circuit: QuantumCircuit
    ) -> QuantumCircuit:
        """
        Generate a Clifford approximation of the input circuit.
        
        This preserves the structure while allowing efficient simulation.
        """
        # Clone circuit
        clifford_circ = circuit.copy()
        
        # Replace non-Clifford gates with Clifford equivalents
        # T gates -> S gates (approximation)
        # Rz(theta) -> Rz(pi/2) approximations
        
        from qiskit.circuit.library import RZGate, RXGate, RYGate
        
        for i, instruction in enumerate(clifford_circ.data):
            op = instruction[0]
            if op.name in ["t", "tdg"]:
                # Replace T with S (Clifford approximation)
                clifford_circ.data[i] = (clifford_circ.s, instruction[1], instruction[2])
            elif op.name == "rz":
                # Approximate Rz with nearest Clifford rotation
                angle = op.params[0]
                clifford_angle = round(angle / (np.pi/2)) * (np.pi/2)
                clifford_circ.data[i] = (RZGate(clifford_angle), instruction[1], instruction[2])
                
        return clifford_circ
    
    def _evaluate_sequence(
        self,
        circuit: QuantumCircuit,
        sequence_name: str,
        pass_names: List[str],
    ) -> float:
        """
        Evaluate a pass sequence on a circuit.
        
        Returns a score (lower is better) based on:
        - Gate count reduction
        - Depth reduction
        - 2-qubit gate reduction
        """
        # Build pass manager
        passes = []
        for name in pass_names:
            config = next((p for p in PASS_CONFIGS if p.name == name), None)
            if config:
                if config.params:
                    passes.append(config.pass_class(**config.params))
                else:
                    passes.append(config.pass_class())
                    
        pm = PassManager(passes)
        
        # Apply passes
        try:
            optimized = pm.run(circuit)
        except Exception:
            return float('inf')
            
        # Calculate score
        original_features = CircuitFeatures.extract(circuit)
        optimized_features = CircuitFeatures.extract(optimized)
        
        # Weighted score (lower is better)
        score = (
            0.4 * optimized_features["depth"] / max(original_features["depth"], 1) +
            0.4 * optimized_features["num_2q_gates"] / max(original_features["num_2q_gates"], 1) +
            0.2 * optimized_features["size"] / max(original_features["size"], 1)
        )
        
        return score
    
    def _select_best_sequence(self, circuit: QuantumCircuit) -> str:
        """Select the best pass sequence for a circuit."""
        # Generate Clifford approximation for fast benchmarking
        clifford_circuit = self._generate_clifford_approximation(circuit)
        
        best_score = float('inf')
        best_sequence = "medium"  # default
        
        for seq_name, pass_names in self.pass_sequences.items():
            score = self._evaluate_sequence(clifford_circuit, seq_name, pass_names)
            
            if score < best_score:
                best_score = score
                best_sequence = seq_name
                
        return best_sequence
    
    def run(self, dag):
        """
        Run OPTRAN pass selection on the DAG.
        
        Args:
            dag: Input DAG circuit
            
        Returns:
            Optimized DAG circuit
        """
        circuit = dag.to_circuit()
        
        # Select best sequence if not cached
        if self._best_sequence is None:
            self._best_sequence = self._select_best_sequence(circuit)
            
        # Apply best sequence
        pass_names = self.pass_sequences[self._best_sequence]
        passes = []
        
        for name in pass_names:
            config = next((p for p in PASS_CONFIGS if p.name == name), None)
            if config:
                if config.params:
                    passes.append(config.pass_class(**config.params))
                else:
                    passes.append(config.pass_class())
                    
        pm = PassManager(passes)
        optimized = pm.run(circuit)
        
        # Convert back to DAG
        from qiskit.converters import circuit_to_dag
        return circuit_to_dag(optimized)


class AdaptiveOptimizationPass(TransformationPass):
    """
    Adaptive optimization that selects passes based on circuit structure.
    
    Simpler and faster than OPTRAN for most use cases.
    """
    
    def __init__(self, target_gateset: Optional[set] = None):
        super().__init__()
        self.target_gateset = target_gateset or {"cx", "rz", "rx", "ry", "h"}
        
    def run(self, dag):
        """Run adaptive optimization."""
        circuit = dag.to_circuit()
        features = CircuitFeatures.extract(circuit)
        
        passes = [Optimize1qGates(), CXCancellation()]
        
        # Add heavier passes for larger circuits
        if features["num_2q_gates"] > 50:
            passes.append(Collect2qBlocks())
            passes.append(ConsolidateBlocks())
            
        pm = PassManager(passes)
        optimized = pm.run(circuit)
        
        from qiskit.converters import circuit_to_dag
        return circuit_to_dag(optimized)


__all__ = [
    "OPTRANPass",
    "AdaptiveOptimizationPass",
    "CircuitFeatures",
    "PASS_CONFIGS",
    "PASS_SEQUENCES",
]
