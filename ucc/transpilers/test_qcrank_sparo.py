"""Unit tests for QCrank and SPARO passes."""
import pytest
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit

def test_qcrank_import():
    from ucc.transpilers.qcrank_pass import QCrankPass
    assert QCrankPass

def test_qcrank_init():
    from ucc.transpilers.qcrank_pass import QCrankPass
    p = QCrankPass(n_nodes=4)
    assert p.n_nodes == 4

def test_qcrank_run():
    from ucc.transpilers.qcrank_pass import QCrankPass
    p = QCrankPass()
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    dag = qc.to_dag()
    result = p.run(dag)
    assert isinstance(result, DAGCircuit)

def test_sparo_import():
    from ucc.transpilers.sparo_pass import SPAROPass
    assert SPAROPass

def test_sparo_init():
    from ucc.transpilers.sparo_pass import SPAROPass
    p = SPAROPass(mct_approximation=3)
    assert p.mct_approximation == 3

def test_sparo_run():
    from ucc.transpilers.sparo_pass import SPAROPass
    p = SPAROPass()
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    dag = qc.to_dag()
    result = p.run(dag)
    assert isinstance(result, DAGCircuit)
