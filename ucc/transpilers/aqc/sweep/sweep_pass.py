from qiskit.converters import dag_to_circuit, circuit_to_dag
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit


class StateSweepPass(TransformationPass):
    """Approximately compiles a quantum circuit using sweeping."""

    def __init__(self):
        super().__init__()

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        from . import approx_state_compile

        qiskit_circuit = dag_to_circuit(dag)

        return circuit_to_dag(approx_state_compile(qiskit_circuit))


class UnitarySweepPass(TransformationPass):
    """Approximately compiles a quantum circuit using sweeping."""

    def __init__(self):
        super().__init__()

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        from . import approx_unitary_compile

        qiskit_circuit = dag_to_circuit(dag)

        return circuit_to_dag(approx_unitary_compile(qiskit_circuit))
