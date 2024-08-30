from pytket import Circuit as TketCircuit
from cirq import Circuit as CirqCircuit
from qiskit import QuantumCircuit as QiskitCircuit

import qiskit.qasm2 
import qiskit.qasm3

from quantum_translator import QiskitInterface, TKETInterface, CirqInterface

class QuantumTranslator:
    @staticmethod
    def supported_types():
        return "pytket.Circuit, cirq.Circuit, qiskit.QuantumCircuit, OpenQASM2"
    
    @classmethod
    def to_qasm(cls, circuit, version='2'):
        # TODO: perhaps this class should have a persistent variable holding 
        # the original circuit so that the user can get their preferred output 
        # back
        """
        Identify type of the provided circuit, and if supported, translate to 
        OpenQASM of the version specified.
        
        Parameters:
            circuit (str): A quantum circuit of supported types 
                (qiskit, cirq, pytket).
            version (str): OpenQASM version to translate the given `circuit` to.
                Defaults to '2'.
        Returns:
            str: OpenQASM2 or OpenQASM3 code corresponding to given `circuit`.
        """
        if isinstance(circuit, TketCircuit):
            return TKETInterface.to_qasm(circuit)

        elif isinstance(circuit, QiskitCircuit):
            return QiskitInterface.to_qasm(circuit, version)

        elif isinstance(circuit, CirqCircuit):
            return CirqInterface.to_qasm(circuit)

        elif isinstance(circuit, str):
            # Check if the string is already OpenQASM; if so, return
            if cls.is_valid_openqasm(circuit, version=version):
                return circuit

        raise TypeError(f'Provided circuit is not in {cls.supported_types()}')
    

    @staticmethod
    def is_valid_openqasm(qasm_output, version):
        """
        Check if the provided string is valid OpenQASM code of the version specified.

        Parameters:
            qasm_output (str): The OpenQASM code as a string.

        Returns:
            bool: True if the string is valid OpenQASM of the version 
            specified, False otherwise.
        """
        if version == '3':
            try:
                qiskit.qasm3.loads(qasm_output)
                return True
            except qiskit.qasm3.exceptions.QASM3ImporterError as a:
                print(a)
                return False
        elif version == '2':
            try:
                qiskit.qasm2.loads(qasm_output)
                return True
            except qiskit.qasm2.QASM2ParseError:
                return False
