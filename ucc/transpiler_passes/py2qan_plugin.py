from qiskit import QuantumCircuit
from qiskit.transpiler import TransformationPass
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.qasm2 import dumps

from py2qan import HeuristicMapper, QuRouter

class Py2QAN_Routing(TransformationPass):

    def __init__(self, init_map, coupling_map):
        super().__init__()
        self.init_map = init_map
        self.coupling_map = coupling_map

    def run(self, dag):
        qasm_rep = dumps(dag_to_circuit(dag))
        # hmapper = HeuristicMapper(qasm_rep, coupling_map=self.coupling_map)
        # init_map = hmapper.run_qiskit(max_iterations=5)
        router = QuRouter(qasm_rep, init_map=self.init_map, coupling_map=self.coupling_map)
        routed_circ, _ = router.run(layers=1, msmt=False)
        return circuit_to_dag(QuantumCircuit.from_qasm_str(routed_circ))