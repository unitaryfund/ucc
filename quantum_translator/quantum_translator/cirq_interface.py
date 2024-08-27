import cirq

class CirqInterface:
    @staticmethod
    def translate_to_qasm(circuit: cirq.Circuit) -> str:
        """Translates a Cirq circuit to OpenQASM2.  OpenQASM3 is not currently supported by Cirq."""
        return cirq.qasm(circuit)
