from qiskit.converters import dag_to_circuit, circuit_to_dag
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit
from . import approx_compile


class MPSPass(TransformationPass):
    """Approximately compiles a quantum circuit using MPS IR to a staircase circuit
    using O(N) circuit depth.

    By default, the compiler uses `mps_sequential.py`, which provides a vanilla implementation
    of the encoding. To opt for the more performant version, install `qmprs` and the compiler
    will automatically use it.

    Below is the link to the repository:
    https://github.com/Qualition/qmprs
    """

    def __init__(self):
        super().__init__()

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        qiskit_circuit = dag_to_circuit(dag)

        return circuit_to_dag(approx_compile(qiskit_circuit))
