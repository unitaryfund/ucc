from .qiskit_interface import QiskitInterface
from .cirq_interface import CirqInterface
from .tket_interface import TKETInterface

class OpenQASMTranslator:
    @staticmethod
    def translate(circuit) -> str:
        """Determines the circuit type and translates to OpenQASM3."""
        if isinstance(circuit, QiskitInterface):
            return QiskitInterface.translate_to_qasm(circuit)
        elif isinstance(circuit, CirqInterface):
            return CirqInterface.translate_to_qasm(circuit)
        elif isinstance(circuit, TKETInterface):
            return TKETInterface.translate_to_qasm(circuit)
        else:
            raise ValueError("Unsupported circuit type.")
