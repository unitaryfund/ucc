"""Unit tests for SEQC and PCOAST passes."""

import pytest
pytest.importorskip("qiskit")
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit


class TestSEQCPCOAST:
    def test_seqc_pass_import(self):
        from ucc.transpilers.seqc_pass import SEQCPass, ChipletConfig, InterChipletLink
        assert SEQCPass is not None

    def test_pcoast_pass_import(self):
        from ucc.transpilers.pcoast_pass import PCOASTPass
        assert PCOASTPass is not None

    def test_seqc_config_dataclass(self):
        from ucc.transpilers.seqc_pass import ChipletConfig
        config = ChipletConfig(chiplet_id=0, num_qubits=5, intra_links=[])
        assert config.chiplet_id == 0

    def test_inter_link_dataclass(self):
        from ucc.transpilers.seqc_pass import InterChipletLink
        link = InterChipletLink(chiplet_a=0, chiplet_b=1, qubit_a=0, qubit_b=0, fidelity=0.99, latency=100)
        assert link.fidelity == 0.99

    def test_pcoast_can_init(self):
        from ucc.transpilers.pcoast_pass import PCOASTPass
        pass_obj = PCOASTPass()
        assert pass_obj is not None

    def test_seqc_run_returns_dag(self):
        from ucc.transpilers.seqc_pass import SEQCPass, ChipletConfig, InterChipletLink
        chip = ChipletConfig(chiplet_id=0, num_qubits=5, intra_links=[])
        link = InterChipletLink(chiplet_a=0, chiplet_b=1, qubit_a=0, qubit_b=0, fidelity=0.99, latency=100)
        pass_obj = SEQCPass(chiplets=[chip], inter_links=[link])
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        dag = qc.to_dag()
        result = pass_obj.run(dag)
        assert isinstance(result, DAGCircuit)

    def test_pcoast_run_returns_dag(self):
        from ucc.transpilers.pcoast_pass import PCOASTPass
        pass_obj = PCOASTPass()
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cx(0, 1)
        dag = qc.to_dag()
        result = pass_obj.run(dag)
        assert isinstance(result, DAGCircuit)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
