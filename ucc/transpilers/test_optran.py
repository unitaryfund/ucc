"""Unit tests for OPTraN pass."""
import pytest
from qiskit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit

def test_optran_import():
    from ucc.transpilers.optran_pass import OPTraNPass
    assert OPTraNPass

def test_optran_init():
    from ucc.transpilers.optran_pass import OPTraNPass
    p = OPTraNPass(max_iterations=10)
    assert p.max_iterations == 10

def test_optran_run():
    from ucc.transpilers.optran_pass import OPTraNPass
    p = OPTraNPass()
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    dag = qc.to_dag()
    result = p.run(dag)
    assert isinstance(result, DAGCircuit)
