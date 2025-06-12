import numpy as np
from numpy.typing import NDArray
import psutil
from qiskit.quantum_info import partial_trace, entropy


def calculate_entanglement_entropy_slope(
    state: NDArray[np.complex128],
) -> float:
    """Calculate the slope of the entanglement entropy as the
    subsystem size increases, which can indicate whether the
    entanglement is volume-law or area-law. This returns a float
    as opposed to a string to provide a more dynamic response.

    Args:
        state (NDArray[np.complex128]): The quantum state represented as a statevector.

    Returns:
        float: The entanglement entropy of the state.
    """
    n = int(np.ceil(np.log2(len(state))))

    entropies = []
    for k in range(1, n // 2 + 1):
        # Trace out rest of the qubits
        rho_A = partial_trace(state, list(range(k, n)))
        S = entropy(rho_A, base=2)
        entropies.append(S)

    # Check if the entropies form a straight line or a curve
    entropies = np.array(entropies[len(entropies) // 2 :])
    x = np.arange(1, len(entropies) + 1)

    # Linear regression: fit y = ax + b
    x_mean = np.mean(x)
    y_mean = np.mean(entropies)

    numerator = np.sum((x - x_mean) * (entropies - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    slope = numerator / denominator if denominator != 0 else 0

    return slope


def has_enough_memory(num_qubits: int) -> tuple[bool, float, float]:
    """Check if the available user RAM is enough to represent
    the statevector IR.

    Args:
        num_qubits (int): The number of qubits for the statevector.

    Returns:
        has_memory (bool): Whether the user has enough RAM.
        memory_required_gb (float): Amount of memory required to
            store the statevector IR in GB.
        available_memory_gb (float): Amount of free memory that
            can be dedicated to storing the statevector IR in GB.
    """
    available_memory_gb = psutil.virtual_memory().available
    available_memory_gb = available_memory_gb / 2**30

    # Calculate approximately how much memory the statevector
    # requires at worst-case (volume-law)
    # statevectors use np.complex128 which needs 16 bytes
    # Use half of the memory available to store the IR
    memory_required_gb = 2 ** (4 + num_qubits - 31)
    has_memory = memory_required_gb <= available_memory_gb

    return has_memory, memory_required_gb, available_memory_gb
