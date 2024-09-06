from pytket import Circuit as TketCircuit
from cirq import Circuit as CirqCircuit
from qiskit import QuantumCircuit as QiskitCircuit

from cirq.contrib.qasm_import import circuit_from_qasm as cirq_from_qasm
from pytket.qasm import circuit_from_qasm_str as tket_from_qasm

import qiskit.qasm2 
import qiskit.qasm3

from .interfaces import QiskitInterface, TKETInterface, CirqInterface

class QuantumTranslator:
    def __init__(self, circuit, return_format):
        self._original_circuit = circuit
        self._original_format = self.identify_format(circuit)

        if return_format == 'original':
            self.return_format = self._original_format
        else:
            self.return_format = return_format

    @property
    def supported_circuit_formats():
        return ["pytket.Circuit", "cirq.Circuit", "qiskit.QuantumCircuit", "OpenQASM2"]

    @classmethod
    def identify_format(cls, circuit):
        if isinstance(circuit, TketCircuit):
            return 'tket'
        elif isinstance(circuit, QiskitCircuit):
            return 'qiskit'
        elif isinstance(circuit, CirqCircuit):
            return 'cirq'
        elif cls.is_valid_openqasm(circuit, version=2):
            return 'openqasm2'
        elif cls.is_valid_openqasm(circuit, version=3):
            return 'openqasm3'
        else:
            return 'unknown'

    @classmethod   
    def to_qasm(cls, circuit, version='2'):
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
        circuit_format = cls.identify_format(circuit)

        match circuit_format:
            case 'tket':
                return TKETInterface.to_qasm(circuit)
            case 'qiskit':
                return QiskitInterface.to_qasm(circuit, version)
            case 'cirq':
                return CirqInterface.to_qasm(circuit)
            case 'openqasm2':
                if version == '2':
                    return circuit # Circuit is already OpenQasm2
                elif version == '3': 
                    # Translate to Qiskit, then to OpenQASM3
                    qis_circuit = cls.to_qiskit(circuit)
                    return QiskitInterface.to_qasm(qis_circuit, version='2')
            case 'openqasm3':
                if version == '3':
                    return circuit # Circuit is already OpenQasm3
                elif version == '2': 
                    # Translate to Qiskit, then to OpenQASM2
                    qis_circuit = cls.to_qiskit(circuit)
                    return QiskitInterface.to_qasm(qis_circuit, version='3')

        raise TypeError(f'Provided circuit is not in {cls.supported_circuit_formats}')
    
    def to_return_format(self, qasm_circuit):
        """Translates given OpenQASM `qasm_circuit` to format of `self.return_type`."""
        match self.return_type:
            case 'tket':
                return self.to_tket(qasm_circuit)
            case 'qiskit':
                return self.to_qiskit(qasm_circuit)
            case 'cirq':
                return self.to_cirq(qasm_circuit)
            case 'openqasm2':
                return self.to_qasm(qasm_circuit, version='2')
            case 'openqasm3':
                return self.to_qasm(qasm_circuit, version='3')


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
            except Exception as a:
                print(a)
                return False
        elif version == '2':
            try:
                qiskit.qasm2.loads(qasm_output)
                return True
            except Exception as a:
                print(a)
                return False
