from qiskit import transpile, QuantumCircuit
from qiskit.providers import BackendV2
from qiskit.transpiler import CouplingMap


from ucc.transpilers.ucc_defaults import UCCDefault1


class UCCTranspiler:
    @staticmethod
    def transpile(circuit, target = None, mode: str = 'ucc', get_gate_counts = False) -> str:
        """
        Transpiles the given quantum `circuit` using either default Qiskit or UCC default compiler passes, as specified by the `mode`.
        
        Parameters:
            circuit (qiskit.QuantumCircuit): The Qiskit circuit to transpile.
            mode (str): 'qiskit' or 'ucc', specifies which set of transpiler    passes to use.
            backend: Can be a Qiskit backend or coupling map, or a list of connections between qubits. If None, all-to-all connectivity is assumed.
                        If Qiskit backend or coupling map, only the coupling list extracted from the backend is used.

        Returns:
            QuantumCircuit: The transpiled quantum circuit.
        """
        if mode == 'ucc':
            if target is None:
                coupling_list = None
            elif isinstance(target, BackendV2):
                coupling_list = list(target.coupling_map.get_edges())
            elif isinstance(target, CouplingMap):
                coupling_list = target.get_edges()
            elif isinstance(target, list):
                coupling_list = target
            else:
                raise ValueError("Invalid backend type. Must be a Qiskit backend, coupling map, or a list of connections between qubits.")
        
        # Transpile the circuit
        if mode == 'qiskit':
            transpiled_circuit = transpile(circuit, optimization_level=3, backend = target)
        elif mode == 'ucc':
            ucc_transpiler = UCCDefault1()
            transpiled_circuit = ucc_transpiler.run(circuit, coupling_list=coupling_list)

        if get_gate_counts:
            gate_counts = transpiled_circuit.count_ops()
        else:
            gate_counts = None
        
        return transpiled_circuit, gate_counts

