"""Tests for CCMap Pass"""

import pytest
from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from qiskit.test.mock import FakeManhattan

from .ccmap_pass import CCMapPass
from .partition import partition_circuit
from .cost_metric import CouplerCostMetric


def test_ccmap_pass_initialization():
    """Test CCMap pass can be initialized"""
    coupling_map = CouplingMap.from_line(5)
    pass_obj = CCMapPass(coupling_map)
    
    assert pass_obj.coupling_map == coupling_map
    assert pass_obj.cost_weight_fidelity == 0.7
    assert pass_obj.cost_weight_latency == 0.3


def test_partition_simple_circuit():
    """Test circuit partitioning with simple circuit"""
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    
    coupling_map = CouplingMap.from_line(3)
    partitions = partition_circuit(circuit, coupling_map)
    
    assert len(partitions) >= 1
    assert isinstance(partitions[0], QuantumCircuit)


def test_cost_metric_calculation():
    """Test cost metric calculation"""
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    
    calibration_data = {
        'gate_errors': {
            'h_0': 0.001,
            'cx_0,1': 0.01
        }
    }
    
    metric = CouplerCostMetric(calibration_data)
    coupling_map = CouplingMap.from_line(2)
    cost = metric.calculate([circuit], coupling_map)
    
    assert isinstance(cost, float)
    assert cost > 0


def test_ccmap_with_manhattan_backend():
    """Test CCMap with a realistic backend"""
    # Use Manhattan (65 qubits) as example modular system
    backend = FakeManhattan()
    coupling_map = backend.configuration().coupling_map
    
    # Create a test circuit
    circuit = QuantumCircuit(10)
    for i in range(9):
        circuit.h(i)
        circuit.cx(i, i + 1)
    
    # Initialize CCMap pass
    ccmap_pass = CCMapPass(
        coupling_map=CouplingMap(coupling_map),
        calibration_data={}
    )
    
    # Run pass
    from qiskit.converters import circuit_to_dag
    dag = circuit_to_dag(circuit)
    result_dag = ccmap_pass.run(dag)
    
    assert result_dag is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
