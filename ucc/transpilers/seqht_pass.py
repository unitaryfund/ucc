"""
Sequency Hierarchy Truncation (SeqHT) Pass
==========================================

Reduces resources for state preparation and time evolution in quantum simulations
by truncating operators based on sequency.

Reference: https://arxiv.org/abs/2407.13835v1

SeqHT has been shown to reduce circuit depth by ~30% for adiabatic state preparation.
"""

from typing import List, Dict, Optional, Tuple
import numpy as np

from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit
from qiskit import QuantumCircuit
from qiskit.circuit.library import RZGate, RXGate, RYGate, PauliEvolutionGate
from qiskit.quantum_info import SparsePauliOp, Pauli


def compute_sequency(pauli_string: str) -> int:
    """
    Compute the sequency (number of sign changes) of a Pauli string.
    
    Sequency measures the complexity of an operator:
    - Lower sequency = smoother operator = more important
    - Higher sequency = more oscillatory = can often be truncated
    
    Args:
        pauli_string: Pauli operator string (e.g., 'XIZY')
        
    Returns:
        Sequency value (number of transitions)
    """
    sequency = 0
    prev = 'I'
    
    for p in pauli_string:
        if p != 'I' and p != prev and prev != 'I':
            sequency += 1
        if p != 'I':
            prev = p
            
    return sequency


class SequencyTruncationPass(TransformationPass):
    """
    Sequency Hierarchy Truncation (SeqHT) Pass
    
    Truncates operators based on sequency hierarchy to reduce circuit depth
    while preserving accuracy in quantum simulations.
    
    The key insight is that operators with lower sequency contribute more
    significantly to observables, while high-sequency operators can often
    be truncated with minimal impact on results.
    
    Example:
        >>> from ucc.transpilers.seqht_pass import SequencyTruncationPass
        >>> from qiskit import QuantumCircuit
        >>> 
        >>> # Create circuit with many rotation gates
        >>> qc = QuantumCircuit(4)
        >>> # ... add time evolution gates ...
        >>> 
        >>> # Apply SeqHT with sequency cutoff of 3
        >>> seqht = SequencyTruncationPass(max_sequency=3)
        >>> truncated = seqht(qc)
    """
    
    def __init__(
        self,
        max_sequency: int = 4,
        min_coefficient: float = 0.01,
        preserve_ground_state: bool = True,
    ):
        """
        Initialize SeqHT pass.
        
        Args:
            max_sequency: Maximum sequency to preserve (truncate higher)
            min_coefficient: Minimum coefficient magnitude to preserve
            preserve_ground_state: Whether to preserve identity operators
        """
        super().__init__()
        self.max_sequency = max_sequency
        self.min_coefficient = min_coefficient
        self.preserve_ground_state = preserve_ground_state
        
    def _truncate_hamiltonian(
        self, 
        hamiltonian: SparsePauliOp
    ) -> SparsePauliOp:
        """
        Truncate a Hamiltonian based on sequency.
        
        Args:
            hamiltonian: Input Hamiltonian
            
        Returns:
            Truncated Hamiltonian
        """
        # Get Pauli terms
        terms = hamiltonian.to_list()
        
        truncated_terms = []
        total_coeff = 0.0
        preserved_coeff = 0.0
        
        for pauli_str, coeff in terms:
            total_coeff += abs(coeff)
            
            # Compute sequency
            seq = compute_sequency(pauli_str)
            
            # Keep if within cutoff
            if seq <= self.max_sequency and abs(coeff) >= self.min_coefficient:
                truncated_terms.append((pauli_str, coeff))
                preserved_coeff += abs(coeff)
            elif pauli_str == 'I' * len(pauli_str) and self.preserve_ground_state:
                # Always preserve identity
                truncated_terms.append((pauli_str, coeff))
                preserved_coeff += abs(coeff)
                
        # Report truncation ratio
        if total_coeff > 0:
            ratio = preserved_coeff / total_coeff
            # Store as property for reporting
            self.property_set['seqht_preservation_ratio'] = ratio
            self.property_set['seqht_terms_remaining'] = len(truncated_terms)
            self.property_set['seqht_terms_original'] = len(terms)
            
        if not truncated_terms:
            return hamiltonian
            
        return SparsePauliOp.from_list(truncated_terms)
    
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """
        Run SeqHT pass on the DAG.
        
        Args:
            dag: Input DAG circuit
            
        Returns:
            Optimized DAG circuit
        """
        circuit = dag.to_circuit()
        
        # Find Pauli evolution gates
        # These are the main targets for SeqHT
        
        new_circuit = QuantumCircuit(circuit.num_qubits)
        new_circuit.metadata = circuit.metadata.copy()
        
        for instruction in circuit.data:
            op = instruction[0]
            qubits = instruction[1]
            clbits = instruction[2]
            
            # Check if this is a Pauli evolution gate
            if isinstance(op, PauliEvolutionGate):
                # Truncate the operator
                original_op = op.operator
                if isinstance(original_op, SparsePauliOp):
                    truncated_op = self._truncate_hamiltonian(original_op)
                    
                    # Create new evolution gate with truncated operator
                    new_gate = PauliEvolutionGate(
                        truncated_op,
                        time=op.time,
                        synthesis=op._synthesis
                    )
                    new_circuit.append(new_gate, qubits)
                else:
                    new_circuit.append(instruction)
            else:
                # Keep non-evolution gates unchanged
                new_circuit.append(instruction)
                
        from qiskit.converters import circuit_to_dag
        return circuit_to_dag(new_circuit)


class AdaptiveSequencyPass(TransformationPass):
    """
    Adaptive Sequency Truncation that adjusts cutoff based on circuit size.
    
    For larger circuits, uses more aggressive truncation.
    """
    
    def __init__(
        self,
        target_depth_reduction: float = 0.3,
        max_iterations: int = 10,
    ):
        super().__init__()
        self.target_depth_reduction = target_depth_reduction
        self.max_iterations = max_iterations
        
    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run adaptive SeqHT."""
        circuit = dag.to_circuit()
        original_depth = circuit.depth()
        target_depth = int(original_depth * (1 - self.target_depth_reduction))
        
        # Binary search for optimal sequency cutoff
        low, high = 0, circuit.num_qubits
        
        for _ in range(self.max_iterations):
            mid = (low + high) // 2
            
            seqht = SequencyTruncationPass(max_sequency=mid)
            result_dag = seqht.run(dag)
            result_circuit = result_dag.to_circuit()
            
            if result_circuit.depth() <= target_depth:
                high = mid
            else:
                low = mid + 1
                
        # Final pass with optimal cutoff
        seqht = SequencyTruncationPass(max_sequency=high)
        return seqht.run(dag)


def analyze_sequency_distribution(
    hamiltonian: SparsePauliOp
) -> Dict[int, List[Tuple[str, float]]]:
    """
    Analyze the sequency distribution of a Hamiltonian.
    
    Returns operators grouped by sequency level.
    
    Args:
        hamiltonian: Input Hamiltonian
        
    Returns:
        Dictionary mapping sequency to list of (pauli_string, coefficient)
    """
    distribution = {}
    
    for pauli_str, coeff in hamiltonian.to_list():
        seq = compute_sequency(pauli_str)
        if seq not in distribution:
            distribution[seq] = []
        distribution[seq].append((pauli_str, coeff))
        
    return distribution


__all__ = [
    "SequencyTruncationPass",
    "AdaptiveSequencyPass",
    "compute_sequency",
    "analyze_sequency_distribution",
]
