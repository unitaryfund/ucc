"""QMAP Routing Pass for UCC.

This pass uses the MQT QMAP library to map quantum circuits to
specific quantum hardware topologies.

For more information, see:
https://github.com/cda-tum/qmap
"""

from qiskit.converters import dag_to_circuit, circuit_to_dag
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler import CouplingMap
from qiskit.dagcircuit import DAGCircuit
from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps as qasm_dumps
from mqt.core.ir import QuantumComputation
from mqt.qmap.sc import map_, Architecture, Configuration, Method


class QMAPRoutingPass(TransformationPass):
    """Maps quantum circuits to hardware topology using QMAP.

    This pass uses the MQT QMAP library to find optimal qubit routing
    for a given coupling map.
    """

    def __init__(self, coupling_map: CouplingMap = None, method: str = "heuristic"):
        """Initialize the QMAP routing pass.

        Args:
            coupling_map: The coupling map for the target hardware.
                         If None, uses a linear chain.
            method: The mapping method to use ("exact", "heuristic").
                   Defaults to "heuristic".
        """
        super().__init__()
        self.coupling_map = coupling_map
        self.method = method

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Run the QMAP routing pass on the DAG.

        Args:
            dag: The input DAG circuit.

        Returns:
            The routed DAG circuit.
        """
        qiskit_circuit = dag_to_circuit(dag)

        # If no coupling map specified, create a linear chain
        if self.coupling_map is None:
            num_qubits = qiskit_circuit.num_qubits
            self.coupling_map = CouplingMap(
                [[i, i + 1] for i in range(num_qubits - 1)]
            )

        # Convert coupling map to QMAP architecture
        coupling_list = self.coupling_map.get_edges()
        num_qubits = self.coupling_map.size()
        
        # Create architecture from coupling map
        arch = Architecture(num_qubits=num_qubits, coupling_map=coupling_list)

        # Configure mapper
        config = Configuration()
        if self.method == "exact":
            config.method = Method.exact
        else:
            config.method = Method.heuristic

        # Convert qiskit circuit to MQT format
        qasm_str = qasm_dumps(qiskit_circuit)
        qc_ir = QuantumComputation.from_qasm_str(qasm_str)

        # Run QMAP
        mapped_qc, mapping_results = map_(qc_ir, arch, config)

        # Convert back to Qiskit (QMAP returns QASM)
        mapped_qiskit = QuantumCircuit.from_qasm_str(mapped_qc.qasm2_str())

        return circuit_to_dag(mapped_qiskit)


__all__ = ["QMAPRoutingPass"]
