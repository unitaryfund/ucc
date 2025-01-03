import os

from qiskit import QuantumCircuit, user_config
from qiskit.transpiler import TransformationPass, PassManager
from qiskit.transpiler.passes import SabreLayout
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.qasm2 import dumps
from qiskit.utils.parallel import CPU_COUNT

from py2qan import HeuristicMapper, QuRouter


CONFIG = user_config.get_config()


class Py2QAN_Routing(TransformationPass):

    def __init__(self, coupling_map):
        super().__init__()
        self.coupling_map = coupling_map
        self.inner_pm = PassManager()

    def fill_partial_mapping(self, partial_map, coupling_map):
        # Fill the qubit map when #qubits in the circuit is fewer than #qubits in the given topology
        final_map = partial_map.copy()
        n_qbts = len(partial_map)
        device_qubits = []
        for edge in coupling_map:
            for q in edge:
                if q not in device_qubits:
                    device_qubits.append(q)
        unused_dqs = [q for q in device_qubits if q not in partial_map.values()]
        for i in range(len(unused_dqs)):
            final_map[n_qbts+i]=unused_dqs[i]
        return final_map

    def run(self, dag):
        circ = dag_to_circuit(dag)
        # hmapper = HeuristicMapper(qasm_rep, coupling_map=self.coupling_map)
        # init_map = hmapper.run_qiskit(max_iterations=5)
        self.inner_pm.append(
               SabreLayout(
                  self.coupling_map,
                  max_iterations=4,
                  swap_trials=_get_trial_count(20),
                  layout_trials=_get_trial_count(20),
               )
            )
        self.inner_pm.run(circ)
        vpmap = self.inner_pm.property_set["layout"].get_virtual_bits()
        init_map0 = {}
        for k,v in vpmap.items():
            init_map0[k._index]=v
        init_map = self.fill_partial_mapping(init_map0, self.coupling_map)

        router = QuRouter(dumps(circ), init_map=init_map, coupling_map=self.coupling_map)
        routed_circ, _ = router.run(layers=1, msmt=False)
        return circuit_to_dag(QuantumCircuit.from_qasm_str(routed_circ))

def _get_trial_count(default_trials=5):
    if CONFIG.get("sabre_all_threads", None) or os.getenv("QISKIT_SABRE_ALL_THREADS"):
        return max(CPU_COUNT, default_trials)
    return default_trials
