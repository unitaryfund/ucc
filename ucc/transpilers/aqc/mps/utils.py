import numpy as np
from numpy.typing import NDArray
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
