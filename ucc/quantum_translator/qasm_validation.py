import qiskit.qasm3, qiskit.qasm2
from qiskit.qasm3.exceptions import QASM3ImporterError
from qiskit.qasm2 import QASM2ParseError

def is_valid_openqasm(qasm_output, version):
    """
    Check if the provided string is valid OpenQASM code of the version specified.

    Parameters:
        qasm_output (str): The OpenQASM code as a string.

    Returns:
        bool: True if the string is valid OpenQASM of the version specified, False otherwise.
    """
    if version == '3':
        try:
            qiskit.qasm3.loads(qasm_output)
            return True
        except QASM3ImporterError as a:
            print(a)
            return False
    elif version == '2':
        try:
            qiskit.qasm2.loads(qasm_output)
            return True
        except QASM2ParseError:
            return False
