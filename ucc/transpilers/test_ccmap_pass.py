"""Unit tests for CCMapPass - Hardware-aware Compilation for Modular Quantum Systems."""

import pytest
from unittest.mock import Mock, MagicMock, patch

# Skip if qiskit not available
pytest.importorskip("qiskit")

from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from qiskit.dagcircuit import DAGCircuit


class TestCCMapPass:
    """Tests for CCMapPass class."""

    def test_ccmap_pass_import(self):
        """Test that CCMapPass can be imported."""
        from ucc.transpilers.ccmap_pass import CCMapPass
        assert CCMapPass is not None

    def test_coupler_config_dataclass(self):
        """Test CouplerConfig dataclass."""
        from ucc.transpilers.ccmap_pass import CouplerConfig
        config = CouplerConfig(
            chip_a=0, chip_b=1,
            qubits_a=[0, 1, 2], qubits_b=[0, 1, 2],
            fidelity=0.99, latency=100
        )
        assert config.chip_a == 0
        assert config.chip_b == 1
        assert config.fidelity == 0.99

    def test_chip_config_dataclass(self):
        """Test ChipConfig dataclass."""
        from ucc.transpilers.ccmap_pass import ChipConfig
        config = ChipConfig(
            chip_id=0, num_qubits=5,
            coupling_map=[(0,1), (1,2)],
            calibration_data={"T1": 100}
        )
        assert config.chip_id == 0
        assert config.num_qubits == 5

    def test_ccmap_pass_initialization(self):
        """Test CCMapPass can be initialized."""
        from ucc.transpilers.ccmap_pass import CCMapPass, ChipConfig, CouplerConfig
        
        chip = ChipConfig(
            chip_id=0, num_qubits=5,
            coupling_map=[(0,1), (1,2)],
            calibration_data={"T1": 100}
        )
        coupler = CouplerConfig(
            chip_a=0, chip_b=1,
            qubits_a=[0], qubits_b=[0],
            fidelity=0.99, latency=100
        )
        
        pass_obj = CCMapPass(chips=[chip], couplers=[coupler])
        assert len(pass_obj.chips) == 1
        assert len(pass_obj.couplers) == 1

    def test_run_returns_dag(self):
        """Test run() method returns a DAGCircuit."""
        from ucc.transpilers.ccmap_pass import CCMapPass, ChipConfig, CouplerConfig
        
        chip = ChipConfig(chip_id=0, num_qubits=5, coupling_map=[(0,1)], calibration_data={})
        coupler = CouplerConfig(chip_a=0, chip_b=1, qubits_a=[0], qubits_b=[0], fidelity=0.99, latency=100)
        
        pass_obj = CCMapPass(chips=[chip], couplers=[coupler])
        
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        dag = qc.to_dag()
        
        result = pass_obj.run(dag)
        assert isinstance(result, DAGCircuit)

    def test_cost_metric_weights(self):
        """Test cost metric weight configuration."""
        from ucc.transpilers.ccmap_pass import CCMapPass, ChipConfig, CouplerConfig
        
        chip = ChipConfig(chip_id=0, num_qubits=5, coupling_map=[(0,1)], calibration_data={})
        coupler = CouplerConfig(chip_a=0, chip_b=1, qubits_a=[0], qubits_b=[0], fidelity=0.99, latency=100)
        
        pass_obj = CCMapPass(
            chips=[chip], 
            couplers=[coupler],
            cost_weight_fidelity=0.8,
            cost_weight_latency=0.2
        )
        assert pass_obj.cost_weight_fidelity == 0.8
        assert pass_obj.cost_weight_latency == 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
