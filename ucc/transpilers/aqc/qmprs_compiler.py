import numpy as np
from numpy.typing import NDArray
from qmprs.synthesis.mps_encoding import Sequential as QmprsSequential  # type: ignore
from quick.circuit import QiskitCircuit
from qiskit import QuantumCircuit
from .mps_utils import calculate_entanglement_entropy_slope
import warnings
import logging

logger = logging.getLogger(__name__)


class QmprsCompiler:
    """Wrapper for `qmprs.synthesis.mps_encoding.Sequential` to approximately
    compile a statevector to a circuit using MPS encoding.

    For more information, see:
    https://github.com/Qualition/qmprs
    """

    def __init__(self, max_fidelity_threshold=0.9) -> None:
        """Initialize the QmprsCompiler with a target fidelity.

        Args:
            max_fidelity_threshold (float): The maximum fidelity required, after
            which we can stop the encoding to save depth. Defaults to 0.9.
        """
        self.sequential = QmprsSequential(QiskitCircuit)
        self.sequential.fidelity_threshold = max_fidelity_threshold

    @staticmethod
    def optimal_params(statevector: NDArray[np.complex128]) -> tuple[int, int]:
        """Calculate the optimal number of layers and sweeps for the
        MPS encoding.

        Users should overwrite this static method to customize the definition
        of the number of layers and number of sweeps for their use-case.

        Args:
            statevector (NDArray[np.complex128]): The statevector to analyze.

        Returns:
            tuple[int, int]: A tuple containing the number of layers and sweeps.
        """
        num_qubits = int(np.ceil(np.log2(len(statevector))))
        slope = calculate_entanglement_entropy_slope(statevector)

        # Entanglement entropy slope is between 0 and 1
        # Use a smooth transition between area-law (0 to 0.4) and volume-law (1)
        # The higher the slope, the more layers and sweeps are needed
        num_layers = int((2 + 1 * slope) * num_qubits)
        num_sweeps = int((10 + 20 * slope) * num_qubits)

        return num_layers, num_sweeps

    def __call__(self, statevector: NDArray[np.complex128]) -> QuantumCircuit:
        """Call the instance to create the circuit that encodes the statevector.

        Args:
            statevector (NDArray[np.complex128]): The statevector to convert.

        Returns:
            QuantumCircuit: The generated quantum circuit.
        """
        slope = calculate_entanglement_entropy_slope(statevector)
        if np.isclose(slope, 1, atol=0.1):
            warnings.warn(
                "Warning: The state is volume-law entangled. Compression may be too lossy."
            )

        num_qubits = int(np.ceil(np.log2(len(statevector))))

        # Single qubit statevector is optimal, and cannot be
        # further improved given depth of 1
        if num_qubits == 1:
            circuit = QuantumCircuit(1)
            circuit.initialize(statevector, [0])
            return circuit

        num_layers, num_sweeps = self.optimal_params(statevector)

        circuit = self.sequential.prepare_state(
            statevector=statevector,
            bond_dimension=2**num_qubits,
            num_layers=num_layers,
            num_sweeps=num_sweeps,
        )

        fidelity = np.vdot(circuit.get_statevector(), statevector)
        logger.info(
            f"Fidelity: {fidelity:.4f}, "
            f"Number of qubits: {num_qubits}, "
            f"Number of layers: {num_layers}, "
            f"Number of sweeps: {num_sweeps}"
        )

        return circuit.circuit
