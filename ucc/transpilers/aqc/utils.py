import psutil


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
