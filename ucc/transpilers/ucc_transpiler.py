from qiskit import transpile, QuantumCircuit
from qiskit.providers import BackendV2
from qiskit.transpiler import CouplingMap


from ucc.transpilers.ucc_defaults import UCCDefault1


class UCCTranspiler:
    @staticmethod
    def transpile(circuit, target_device = None, mode: str = 'ucc', get_gate_counts = False) -> str:
        """
        Transpiles the given quantum `circuit` using either default Qiskit or UCC default compiler passes, as specified by the `mode`.
        
        Parameters:
            circuit (qiskit.QuantumCircuit): The Qiskit circuit to transpile.
            mode (str): 'qiskit' or 'ucc', specifies which set of transpiler    passes to use.
            target_device: Can be a Qiskit backend or coupling map, or a list of connections between qubits. If None, all-to-all connectivity is assumed.
                        If Qiskit backend or coupling map, only the coupling list extracted from the backend is used.

        Returns:
            QuantumCircuit: The transpiled quantum circuit.
        """
        if mode in ['ucc', 'ucc-qrack']:
            if target_device is None:
                coupling_list = None
            elif isinstance(target_device, BackendV2):
                coupling_list = list(target_device.coupling_map.get_edges())
            elif isinstance(target_device, CouplingMap):
                coupling_list = target_device.get_edges()
            elif isinstance(target_device, list):
                coupling_list = target_device
            else:
                raise ValueError("Invalid backend type. Must be a Qiskit backend, coupling map, or a list of connections between qubits.")
        
        # Transpile the circuit
        if mode == 'qiskit':
            transpiled_circuit = transpile(circuit, optimization_level=3, backend = target_device)
        elif mode in ['ucc', 'ucc-qrack']:
            is_qrack = (mode=='ucc-qrack')
            ucc_transpiler = UCCDefault1(is_qrack)
            transpiled_circuit = ucc_transpiler.run(circuit, coupling_list=coupling_list)

        if get_gate_counts:
            gate_counts = transpiled_circuit.count_ops()
        else:
            gate_counts = None
        
        return transpiled_circuit, gate_counts

