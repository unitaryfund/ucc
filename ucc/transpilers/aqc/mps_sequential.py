import numpy as np
from numpy.typing import NDArray
import quimb.tensor as qtn  # type: ignore
from qiskit import QuantumCircuit  # type: ignore
from qiskit.quantum_info import Statevector  # type: ignore
from .mps_utils import calculate_entanglement_entropy_slope
import warnings
import logging

logger = logging.getLogger(__name__)


def gram_schmidt(matrix: NDArray[np.complex128]) -> NDArray[np.complex128]:
    """Perform Gram-Schmidt orthogonalization on the columns of a matrix
    to define the unitary block to encode the MPS.

    Notes
    -----
    If a column is (approximately) zero, it is replaced with a random vector.

    Args:
        matrix (NDArray[np.complex128]): Input matrix with complex entries.

    Returns:
        unitary (NDArray[np.complex128]): A unitary matrix with orthonormal columns
            derived from the input matrix. If a column is (approximately) zero, it
            is replaced with a random vector.
    """
    num_rows, num_columns = matrix.shape
    unitary = np.zeros((num_rows, num_columns), dtype=np.complex128)
    orthonormal_basis: list[NDArray[np.complex128]] = []

    for j in range(num_columns):
        column = matrix[:, j]

        # If column is (approximately) zero, replace with random
        if np.allclose(column, 0):
            column = np.random.uniform(-1, 1, num_rows)  # type: ignore
            if np.iscomplexobj(matrix):
                column = column + 1j * np.random.uniform(-1, 1, num_rows)

        # Gram-Schmidt orthogonalization
        for basis_vector in orthonormal_basis:
            column -= (basis_vector.conj().T @ column) * basis_vector

        # Handle near-zero vectors (linear dependence)
        norm = np.linalg.norm(column)
        if norm < 1e-12:
            is_complex = np.iscomplexobj(matrix)
            column = np.random.uniform(-1, 1, num_rows)  # type: ignore
            if is_complex:
                column += 1j * np.random.uniform(-1, 1, num_rows)
            for basis_vector in orthonormal_basis:
                column -= (basis_vector.conj().T @ column) * basis_vector

        unitary[:, j] = column / np.linalg.norm(column)
        orthonormal_basis.append(unitary[:, j])

    return unitary


class Sequential:
    def __init__(self, max_fidelity_threshold: float = 0.95) -> None:
        """Initialize the Sequential class.

        Args:
            max_fidelity_threshold (float): The maximum fidelity required, after
            which we can stop the encoding to save depth. Defaults to 0.95.
        """
        self.max_fidelity_threshold = max_fidelity_threshold

    def generate_layer(
        self, mps: qtn.MatrixProductState
    ) -> list[tuple[list[int], NDArray[np.complex128]]]:
        """Convert a Matrix Product State (MPS) to a circuit representation
        using a single unitary layer.

        Args:
            mps (qtn.MatrixProductState): The MPS to convert.

        Returns:
            unitary_layer (list[tuple[list[int], NDArray[np.complex128]]]): A list of
            tuples representing the unitary layer of the circuit.
                Each tuple contains:
                - A list of qubit indices (in LSB order) that the unitary acts on.
                - A unitary matrix (as a 2D NumPy array) that encodes the MPS.
        """
        num_sites = mps.L

        unitary_layer: list[tuple[list[int], NDArray[np.complex128]]] = []

        for i, tensor in enumerate(reversed(mps.arrays)):
            i = num_sites - i - 1

            # MPS representation uses 1D entanglement, thus we need to define
            # the range of the indices via the tensor shape
            # i.e., if q0 and q3 are entangled, then regardless of q1 and q2 being
            # entangled the entanglement range would be q0-q3
            if i == 0:
                d_right, d = tensor.shape
                tensor = tensor.reshape((1, d_right, d))
            if i == num_sites - 1:
                d_left, d = tensor.shape
                tensor = tensor.reshape((d_left, 1, d))

            tensor = np.swapaxes(tensor, 1, 2)

            # Combine the physical index and right-virtual index of the tensor to construct an isometry
            # matrix
            d_left, d, d_right = tensor.shape
            isometry = tensor.reshape((d * d_left, d_right))

            # Put qubit ordering in LSB (we provide this so that users can modify between LSB and MSB)
            # To put into MSB, comment the second line below
            qubits = reversed(range(i - int(np.ceil(np.log2(d_left))), i + 1))
            qubits = [abs(qubit - num_sites + 1) for qubit in qubits]  # type: ignore

            # Create all-zero matrix and add the isometry columns
            matrix = np.zeros(
                (isometry.shape[0], isometry.shape[0]), dtype=isometry.dtype
            )

            # Keep columns for which all ancillas are in the zero state
            matrix[:, : isometry.shape[1]] = isometry

            # Perform Gram-Schmidt orthogonalization to ensure the columns are orthonormal
            unitary = gram_schmidt(matrix)

            # Store the unitary layer for the circuit
            unitary_layer.append((qubits, unitary))  # type: ignore

        return unitary_layer

    def mps_to_circuit_approx(
        self,
        statevector: NDArray[np.complex128],
        max_num_layers: int,
        chi_max: int,
    ) -> QuantumCircuit:
        r"""Approximately encodes the MPS into a circuit via multiple layers
        of exact encoding of bond 2 truncated MPS.

        Whilst we can encode the MPS exactly in a single layer, we require
        $log(chi) + 1$ qubits for each tensor, which results in larger circuits.
        This function uses bond 2 which allows us to encode the MPS using one and
        two qubit gates, which results in smaller circuits, and easier to run on
        hardware.

        This is the core idea of Ran's paper [1].

        [1] https://arxiv.org/abs/1908.07958

        Args:
            statevector (NDArray[np.complex128]): The statevector to convert.
            max_num_layers (int): The number of layers to use in the circuit.

        Returns:
            QuantumCircuit: The generated quantum circuit that encodes the MPS.
        """
        mps = qtn.MatrixProductState.from_dense(statevector)
        mps: qtn.MatrixProductState = (
            qtn.tensor_1d_compress.tensor_network_1d_compress(
                mps, max_bond=chi_max
            )
        )  # type: ignore
        mps.permute_arrays()

        mps.compress(form="left", max_bond=chi_max)
        mps.left_canonicalize(normalize=True)

        compressed_mps = mps.copy(deep=True)
        disentangled_mps = mps.copy(deep=True)

        circuit = QuantumCircuit(mps.L, mps.L)

        unitary_layers = []

        # Initialize the zero state |00...0> to serve as comparison
        # for the disentangled MPS
        zero_state = np.zeros((2**mps.L,), dtype=np.complex128)
        zero_state[0] = 1.0  # |00...0> state

        # Ran's approach uses a iterative disentanglement of the MPS
        # where each layer compresses the MPS to a maximum bond dimension of 2
        # and applies the inverse of the layer to disentangle the MPS
        # After a few layers we are adequately close to |00...0> state
        # after which we can simply reverse the layers (no inverse) and apply them
        # to the |00...0> state to obtain the MPS state
        for layer_index in range(max_num_layers):
            # Compress the MPS from the previous layer to a maximum bond dimension of 2,
            # |ψ_k> -> |ψ'_k>
            compressed_mps = disentangled_mps.copy(deep=True)

            # Normalize improves fidelity of the encoding
            compressed_mps.normalize()
            compressed_mps.compress(form="left", max_bond=2)

            # Generate unitary layer
            unitary_layer = self.generate_layer(compressed_mps)
            unitary_layers.append(unitary_layer)

            # To update the MPS definition, apply the inverse of U_k to disentangle |ψ_k>,
            # |ψ_(k+1)> = inv(U_k) @ |ψ_k>
            for i, _ in enumerate(unitary_layer):
                inverse = unitary_layer[-(i + 1)][1].conj().T

                if inverse.shape[0] == 4:
                    disentangled_mps.gate_split_(inverse, (i - 1, i))
                else:
                    disentangled_mps.gate_(inverse, (i), contract=True)

            # Compress the disentangled MPS to a maximum bond dimension of chi_max
            # This is to ensure that the disentangled MPS does not grow too large
            # and improves the fidelity of the encoding
            disentangled_mps: qtn.MatrixProductState = (
                qtn.tensor_1d_compress.tensor_network_1d_compress(  # type: ignore
                    disentangled_mps, max_bond=chi_max
                )
            )

            fidelity = np.vdot(disentangled_mps.to_dense(), zero_state)

            if fidelity >= self.max_fidelity_threshold:
                # If the disentangled MPS is close enough to the zero state,
                # we can stop the disentanglement process
                logger.info(
                    f"Reached target fidelity {fidelity}. "
                    f"{layer_index + 1} layers used."
                )
                break

        if layer_index == max_num_layers - 1:
            logger.info(
                f"Reached fidelity {fidelity} with "
                f"maximum number of layers {max_num_layers}."
            )

        # The layers disentangle the MPS to a state close to |00...0>
        # inv(U_k) ... inv(U_1) |ψ> = |00...0>
        # So, we have to reverse the layers and apply them to the |00...0> state
        # to obtain the MPS state
        # |ψ> = U_1 ... U_k |00...0>
        unitary_layers.reverse()

        # Apply the unitary layers to the |00...0> state
        for unitary_layer in unitary_layers:
            for qubits, unitary in unitary_layer:
                circuit.unitary(unitary, qubits)

        return circuit

    @staticmethod
    def optimal_params(statevector: NDArray[np.complex128]) -> int:
        """Calculate the optimal number of layers and sweeps for the
        MPS encoding.

        Users should overwrite this static method to customize the definition
        of the number of layers and number of sweeps for their use-case.

        Args:
            statevector (NDArray[np.complex128]): The statevector to analyze.

        Returns:
            num_layers (int): The optimal maximum number of layers.
        """
        num_qubits = int(np.ceil(np.log2(len(statevector))))
        slope = calculate_entanglement_entropy_slope(statevector)

        # Entanglement entropy slope is between 0 and 1
        # Use a smooth transition between area-law (0 to 0.4) and volume-law (1)
        # The higher the slope, the more layers are needed
        num_layers = int((2 + 2 * slope) * num_qubits)

        return num_layers

    def __call__(
        self,
        statevector: NDArray[np.complex128],
    ) -> QuantumCircuit:
        """Call the instance to create the circuit that encodes the statevector.

        Args:
            statevector (NDArray[np.complex128]): The statevector to convert.

        Returns:
            QuantumCircuit: The generated quantum circuit.
        """
        num_qubits = int(np.ceil(np.log2(len(statevector))))

        # Single qubit statevector is optimal, and cannot be
        # further improved given depth of 1
        if num_qubits == 1:
            circuit = QuantumCircuit(1)
            circuit.initialize(statevector, [0])
            return circuit

        slope = calculate_entanglement_entropy_slope(statevector)
        if np.isclose(slope, 1, atol=0.1):
            warnings.warn(
                "Warning: The state is volume-law entangled. Compression may be too lossy."
            )

        max_num_layers = self.optimal_params(statevector)

        circuit = self.mps_to_circuit_approx(
            statevector, max_num_layers, 2**num_qubits
        )

        fidelity = np.vdot(Statevector(circuit).data, statevector)
        logger.info(
            f"Fidelity: {fidelity:.4f}, "
            f"Number of qubits: {num_qubits}, "
            f"Number of layers: {max_num_layers}, "
        )

        return circuit
