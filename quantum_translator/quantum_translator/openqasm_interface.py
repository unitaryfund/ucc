from pytket import Circuit as TketCircuit
from cirq import Circuit as CirqCircuit
from qiskit import QuantumCircuit as QiskitCircuit

from cirq.contrib.qasm_import import circuit_from_qasm as cirq_from_qasm
from pytket.qasm import circuit_from_qasm_str as tket_from_qasm
import qiskit.qasm2 
import qiskit.qasm3


class OpenQASMInterface:

    @staticmethod
    def is_valid_openqasm(qasm_output, version):
        """
        Check if the provided string is valid OpenQASM code of the version specified.

        Parameters:
            qasm_output (str): The OpenQASM code as a string.

        Returns:
            bool: True if the string is valid OpenQASM of the version specified, False otherwise.
        """
        if version == '2':
            try:
                qiskit.qasm2.loads(qasm_output)
                return True
            except qiskit.qasm2.QASM2ParseError:
                return False
        elif version == '3':
            try:
                qiskit.qasm3.loads(qasm_output)
                return True
            except qiskit.qasm3.exceptions.QASM3ImporterError as a:
                print(a)
                return False

    @classmethod
    def to_tket(cls, qasm_circuit: str) -> TketCircuit:
        """Validates and translates an OpenQASM2 string to a TKET circuit. 
        OpenQASM3 is not currently supported by PyTKET."""

        assert cls.is_valid_openqasm(qasm_circuit, version='2')
        return tket_from_qasm(qasm_circuit)

    @classmethod
    def to_cirq(cls, qasm_circuit: str) -> CirqCircuit:
        """Validates and translates an OpenQASM2 string to a cirq circuit. 
        OpenQASM3 is not currently supported by Cirq."""

        assert cls.is_valid_openqasm(qasm_circuit, version='2')
        return cirq_from_qasm(qasm_circuit)

    @classmethod
    def to_qiskit(cls, qasm_circuit: str) -> QiskitCircuit:
        """Validates and translates an OpenQASM2 or OpenQASM3 string to a Qiskit circuit."""

        if cls.is_valid_openqasm(qasm_circuit, version='2'):
            return qiskit.qasm2.loads(qasm_circuit)
        elif cls.is_valid_openqasm(qasm_circuit, version='3'):
            return qiskit.qasm3.loads(qasm_circuit)
        
        