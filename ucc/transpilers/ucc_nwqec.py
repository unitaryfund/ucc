import tempfile
import nwqec
import qiskit
from qiskit.qasm2 import dump, loads
from qiskit.qasm2 import LEGACY_CUSTOM_INSTRUCTIONS


def is_clifford_or_t(gate_name: str) -> bool:
    """Check if a gate is a Clifford or T gate using qiskit naming conventions."""
    clifford_gates = {
        "x",
        "y",
        "z",
        "h",
        "sx",
        "sxdg",
        "s",
        "sdg",
        "cx",
        "cz",
        "swap",
        "id",
    }
    t_gates = {"t", "tdg"}
    return gate_name in clifford_gates or gate_name in t_gates


class CliffordTPass(qiskit.transpiler.basepasses.TransformationPass):
    """
    A transpiler pass that applies NWQEC's Clifford+T translation to a Qiskit DAGCircuit, lowering
    the circuit to Clifford+T form.
    """

    def __init__(
        self,
        keep_ccx: bool = False,
        epsilon: float | None = None,
    ):
        """
        Args:
            keep_ccx: preserve CCX gates when True.
            epsilon: absolute error tolerance for RZ synthesis;
                     defaults to abs(theta) * nwqec.DEFAULT_EPSILON_MULTIPLIER per angle.
        """
        super().__init__()
        self._keep_ccx = keep_ccx
        self._epsilon = epsilon

    def run(self, dag):
        circuit = qiskit.converters.dag_to_circuit(dag)

        with tempfile.NamedTemporaryFile(suffix=".qasm") as tmp:
            tmp_qasm = tmp.name
            dump(circuit, tmp_qasm)
            nwqec_circuit = nwqec.load_qasm(tmp_qasm)

            nwqec_circuit = nwqec.to_clifford_t(
                nwqec_circuit, epsilon=self._epsilon, keep_ccx=self._keep_ccx
            )
            return qiskit.converters.circuit_to_dag(
                loads(
                    nwqec_circuit.to_qasm(),
                    custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS,
                )
            )


class CliffordReduction(qiskit.transpiler.basepasses.TransformationPass):
    """
    A transpiler pass that applies NWQEC's Clifford Reduction optimization to a Qiskit DAGCircuit.
    Applies the Clifford reduction optimization (preserves parallelism while reducing non-T overhead).
    Based on the technique from Wang et al. "Optimizing FTQC Programs through QEC Transpiler and Architecture Codesign" (2024).
    """

    def __init__(
        self,
        epsilon: float | None = None,
    ):
        """
        Args:
            epsilon: absolute error tolerance for RZ synthesis;
                     defaults to abs(theta) * nwqec.DEFAULT_EPSILON_MULTIPLIER per angle.
        """
        super().__init__()
        self._epsilon = epsilon

    def run(self, dag):
        circuit = qiskit.converters.dag_to_circuit(dag)

        with tempfile.NamedTemporaryFile(suffix=".qasm") as tmp:
            tmp_qasm = tmp.name
            dump(circuit, tmp_qasm)
            nwqec_circuit = nwqec.load_qasm(tmp_qasm)

            nwqec_circuit = nwqec.to_clifford_reduction(
                nwqec_circuit, epsilon=self._epsilon
            )
            return qiskit.converters.circuit_to_dag(
                loads(
                    nwqec_circuit.to_qasm(),
                    custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS,
                )
            )
