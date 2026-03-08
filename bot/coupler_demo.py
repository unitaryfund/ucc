"""Demo of hardware-aware compilation for coupler-connected systems."""

from ucc.transpilers.coupler import (
    CouplerConnectedArchitecture,
    CouplerCostModel,
    HardwareAwarePlacementPass,
    CouplerAwareRoutingPass,
)
from ucc.transpilers.coupler.coupler_architecture import ChipSpec, CouplerSpec, CouplerLink


def main():
    # Define 4-chip architecture with coherent couplers
    chips = [
        ChipSpec(num_qubits=100, coherence_time=100, single_qubit_fidelity=0.999,
                 two_qubit_fidelity=0.99, gate_latency=40, topology="grid"),
        ChipSpec(num_qubits=100, coherence_time=100, single_qubit_fidelity=0.999,
                 two_qubit_fidelity=0.99, gate_latency=40, topology="grid"),
        ChipSpec(num_qubits=100, coherence_time=100, single_qubit_fidelity=0.999,
                 two_qubit_fidelity=0.99, gate_latency=40, topology="grid"),
        ChipSpec(num_qubits=100, coherence_time=100, single_qubit_fidelity=0.999,
                 two_qubit_fidelity=0.99, gate_latency=40, topology="grid"),
    ]
    
    coupler = CouplerSpec(
        frequency=5.0, coherence_time=50, gate_fidelity=0.95,
        gate_latency=100, max_coupling_strength=50, temperature=15
    )
    
    links = [
        CouplerLink(0, 1, coupler, 5.0, 0.5),
        CouplerLink(1, 2, coupler, 5.0, 0.5),
        CouplerLink(2, 3, coupler, 5.0, 0.5),
        CouplerLink(0, 2, coupler, 10.0, 1.0),
    ]
    
    arch = CouplerConnectedArchitecture(chips, [coupler], links)
    cost_model = CouplerCostModel(arch)
    
    print(arch.summary())
    print(f"Coupler fidelity (0->1): {arch.get_coupler_fidelity(0, 1)}")
    print(f"Coupler latency (0->1): {arch.get_coupler_latency(0, 1)} ns")


if __name__ == "__main__":
    main()
