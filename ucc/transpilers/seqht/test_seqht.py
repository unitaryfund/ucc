"""SeqHT Tests"""

import pytest
from seqht_pass import SeqHTPass, create_seqht_pass


def test_seqht_creation():
    """Test SeqHT pass creation"""
    pass_obj = SeqHTPass(sequency_cutoff=3)
    assert pass_obj.sequency_cutoff == 3


def test_resource_estimation():
    """Test resource estimation"""
    pass_obj = SeqHTPass()
    
    resources = pass_obj.estimate_resources(n_qubits=4)
    
    assert resources["depth_reduction_percent"] == 30
    assert resources["estimated_gates"] > 0


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
