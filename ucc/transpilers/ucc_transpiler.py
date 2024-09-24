from qiskit import transpile, QuantumCircuit
from ..quantum_translator import QuantumTranslator

from ucc.transpilers.ucc_defaults import UCCDefault1


class UCCTranspiler:
    @staticmethod
    def transpile(circuit: str, mode: str = 'ucc', get_gate_counts = False) -> str:
        """
        Transpiles the given quantum `circuit` using either default Qiskit or UCC default compiler passes, as specified by the `mode`.
        
        Parameters:
            circuit (qiskit.QuantumCircuit): The Qiskit circuit to transpile.
            mode (str): 'qiskit' or 'ucc', specifies which set of transpiler    passes to use.

        Returns:
            QuantumCircuit: The transpiled quantum circuit.
        """
        
        # Transpile the circuit
        if mode == 'qiskit':
            transpiled_circuit = transpile(circuit, optimization_level=3)
        elif mode == 'ucc':
            ucc_transpiler = UCCDefault1()
            transpiled_circuit = ucc_transpiler.run(circuit)

        if get_gate_counts:
            gate_counts = transpiled_circuit.count_ops()
        else:
            gate_counts = None
        
        return transpiled_circuit, gate_counts

