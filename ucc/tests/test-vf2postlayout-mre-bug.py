import warnings
from qiskit import QuantumCircuit as QiskitCircuit
from qiskit.providers import BackendV2 as Backend
from qiskit.transpiler import Target, PassManager
from qiskit.providers import Options
from qiskit.circuit.library import CXGate
from qiskit.transpiler.passes import (
    VF2Layout,
    VF2PostLayout,
    ApplyLayout,
)
from qiskit.transpiler.passes.utils import CheckMap
from qiskit.converters import circuit_to_dag


# Define simple backend with only chainwise, unidirectional coupling
class Mybackend(Backend):
    """A mock Qiskit backend for testing purposes.
    Supported operations:
    - CXGate

    Coupling map:
    - 0 -- 1 -- 2
    """

    def __init__(self):
        super().__init__()

        # Create Target
        self._target = Target("Target for My Backend")
        cx_props = {edge: None for edge in [(0, 1), (1, 2)]}
        self._target.add_instruction(CXGate(), cx_props)

    @property
    def target(self):
        return self._target

    @property
    def max_circuits(self):
        return 1024

    @classmethod
    def _default_options(cls):
        return Options(shots=1024, memory=False)

    def run(self, circuit, **kwargs):
        # serialize circuits submit to backend and create a job
        for kwarg in kwargs:
            if not hasattr(kwarg, self.options):
                warnings.warn(
                    "Option %s is not used by this backend" % kwarg,
                    UserWarning,
                    stacklevel=2,
                )
        return None  # Currently not implemented


### Define circuit with CX between qubits 0 and 2 (not directly connected)
circuit = QiskitCircuit(3)
circuit.cx(0, 1)
circuit.cx(0, 2)

### Initialize target
target_device = Mybackend().target

# Define simple pass manager containing only an initial layout and a VF2PostLayout
pass_manager = PassManager()
pass_manager.append(
    VF2Layout(target=target_device)
)  # Required before VF2PostLayout
pass_manager.append(ApplyLayout())
pass_manager.append(VF2PostLayout(target=target_device))
pass_manager.append(ApplyLayout())

result_circuit = pass_manager.run(circuit)

# Check that the compiled circuit respects the coupling map of the target device
coupling_map = target_device.build_coupling_map()
analysis_pass = CheckMap(coupling_map, property_set_field="check_map")

dag = circuit_to_dag(result_circuit)
analysis_pass.run(dag)
assert analysis_pass.property_set["check_map"]
