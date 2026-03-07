"""Test PopQC integration"""

import pytest
from qiskit import QuantumCircuit

try:
    from popqc_pass import PopQCTranspilePass
    POPQC_AVAILABLE = True
except ImportError:
    POPQC_AVAILABLE = False


@pytest.mark.skipif(not POPQC_AVAILABLE, reason="PopQC not installed")
def test_popqc_basic():
    """Test basic PopQC optimization"""
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    
    pass_obj = PopQCTranspilePass()
    optimized = pass_obj.run(circuit)
    
    assert optimized is not None
    assert optimized.num_qubits == 3


@pytest.mark.skipif(not POPQC_AVAILABLE, reason="PopQC not installed")
def test_popqc_benchmark():
    """Test benchmarking functionality"""
    circuit = QuantumCircuit(5)
    for i in range(5):
        circuit.h(i)
    for i in range(4):
        circuit.cx(i, i+1)
    
    pass_obj = PopQCTranspilePass()
    results = pass_obj.benchmark(circuit, num_runs=3)
    
    assert 'speedup' in results
    assert results['speedup'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
