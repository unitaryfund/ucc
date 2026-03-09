"""Unit tests for SeqHT and ODQCR passes."""
import pytest
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit

def test_seqht_import():
    from ucc.transpilers.seqht_pass import SequencyTruncationPass
    assert SequencyTruncationPass

def test_seqht_init():
    from ucc.transpilers.seqht_pass import SequencyTruncationPass
    p = SequencyTruncationPass(threshold=0.5)
    assert p.threshold == 0.5

def test_odqcr_import():
    from ucc.transpilers.odqcr_pass import ODQCRPass
    assert ODQCRPass

def test_odqcr_init():
    from ucc.transpilers.odqcr_pass import ODQCRPass
    p = ODQCRPass(max_layers=5)
    assert p.max_layers == 5

def test_odqcr_run():
    from ucc.transpilers.odqcr_pass import ODQCRPass
    p = ODQCRPass()
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    dag = qc.to_dag()
    result = p.run(dag)
    assert isinstance(result, DAGCircuit)
