from pytket import Circuit
from pytket.qasm import circuit_to_qasm_str

class TKETInterface:
    @staticmethod
    def translate_to_qasm(circuit: Circuit) -> str:
        """Translates a TKET circuit to OpenQASM2. OpenQASM3 is not currently supported by PyTKET."""
        return circuit_to_qasm_str(circuit)
