"""QMAP Integration Tests"""

import pytest
from qmap_pass import QMAPRoutingPass, create_qmap_pass


def test_basic_routing():
    """Test basic QMAP routing"""
    # Simple coupling map (linear topology)
    coupling_map = [[0, 1], [1, 0], [1, 2], [2, 1]]
    
    pass_obj = QMAPRoutingPass(coupling_map)
    assert pass_obj is not None
    

def test_qmap_factory():
    """Test QMAP pass factory"""
    coupling_map = [[0, 1], [1, 0]]
    
    pass0 = create_qmap_pass(coupling_map, optimization_level=0)
    assert pass0.method == "heuristic"
    
    pass2 = create_qmap_pass(coupling_map, optimization_level=2)
    assert pass2.method == "exact"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
