"""Demo of chiplet compilation pipeline.

This demonstrates the SEQC-inspired chiplet compilation pipeline
for modular quantum architectures.
"""

from qiskit import QuantumCircuit
from qiskit.transpilers import PassManager
from ucc.transpilers.chiplet import (
    ChipletArchitecture,
    ChipletPlacementPass,
    ChipletRoutingPass
)


def create_example_circuit() -> QuantumCircuit:
    """Create a circuit with nearest-neighbor interactions."""
    qc = QuantumCircuit(6)
    
    # All-to-all connectivity pattern (will need routing on chiplet arch)
    for i in range(5):
        qc.cx(i, i + 1)
    qc.h(0)
    qc.cx(0, 5)
    qc.cx(2, 4)
    qc.cx(3, 5)
    
    return qc


def main():
    print("=== Chiplet Compilation Demo ===\n")
    
    # Create a 2x2 chiplet architecture (4 chiplets, 10 qubits each)
    arch = ChipletArchitecture.from_grid(
        rows=2, 
        cols=2,
        qubits_per_chiplet=5,
        inter_latency=10.0  # Inter-chiplet gates are 10x slower
    )
    
    print(f"Architecture: {arch.name}")
    print(f"Total qubits: {arch.get_total_qubits()}")
    print(f"Chiplets: {len(arch.chiplets)}")
    print(f"Links: {len(arch.links)}\n")
    
    # Create example circuit
    qc = create_example_circuit()
    print("Input circuit:")
    print(qc.draw())
    print()
    
    # Run placement pass
    from qiskit.converters import circuit_to_dag
    dag = circuit_to_dag(qc)
    
    placement_pass = ChipletPlacementPass(arch)
    dag = placement_pass.run(dag)
    
    print("After placement:")
    print(f"Layout: {dag.layout}\n")
    
    # Run routing pass
    routing_pass = ChipletRoutingPass(arch, optimization_level=1)
    dag = routing_pass.run(dag)
    
    # Convert back to circuit
    routed_qc = dag_to_circuit(dag)
    print("Routed circuit:")
    print(routed_qc.draw())
    
    # Compute latency cost
    cost = routing_pass.compute_latency_cost(dag)
    print(f"\nLatency cost: {cost}")
    print("\nDemo complete!")


if __name__ == "__main__":
    main()
