#Construct a custom compiler
from qiskit import transpile
from qiskit.transpiler import PassManager
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import CollectCliffords, HighLevelSynthesis, HLSConfig
from qiskit.transpiler.passes.synthesis.unitary_synthesis import DefaultUnitarySynthesis


from ..transpiler_passes import BasisTranslator, CommutativeCancellation, Collect2qBlocks, ConsolidateBlocks, UnitarySynthesis, Optimize1qGatesDecomposition, CXCancellation, SpectralMapping, SabreLayout

from qiskit.transpiler.passes import Optimize1qGatesSimpleCommutation

from pyqrack import QrackCircuit



# from ucc_passes.entanglement_net_to_layout import Decompose2qNetworkWithMap

class UCCDefault1:
    def __init__(self, local_iterations=1, is_qrack=False):
        self.pass_manager = PassManager()
        self._1q_basis = ['rz', 'rx', 'ry', 'h']
        self._2q_basis = ['cx']
        self.target_basis = self._1q_basis + self._2q_basis
        self.special_commutations = {
            ("rx", "cx"): {
                (0,): False,
                (1,): True,
            },
            ("rz", "cx"): {
                (0,): True,
                (1,): False,
            },
        }
        if not is_qrack:
            # Since we translate basis at the end of the pass set,
            # we only need one initial basis translation pass on the input,
            # and run() will handle Qrack translation from ['u', 'multiplexer']
            self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis))
        self.add_local_passes(local_iterations)

    @property
    def default_passes(self):
        return 
        
    def add_local_passes(self, local_iterations):
        for _ in range(local_iterations):
            self.pass_manager.append(Optimize1qGatesDecomposition())
            self.pass_manager.append(CommutativeCancellation(standard_gates=self.target_basis, special_commutations=self.special_commutations))
            self.pass_manager.append(Collect2qBlocks())
            self.pass_manager.append(ConsolidateBlocks(force_consolidate=True))
            self.pass_manager.append(UnitarySynthesis(basis_gates=self.target_basis))
            self.pass_manager.append(Optimize1qGatesDecomposition(basis=self._1q_basis))
            self.pass_manager.append(CollectCliffords())
            self.pass_manager.append(HighLevelSynthesis(hls_config=HLSConfig(clifford=["greedy"])))
            self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis))

            #Add following passes if merging single qubit rotations that are interrupted by a commuting 2 qubit gate is desired
            # self.pass_manager.append(Optimize1qGatesSimpleCommutation(basis=self._1q_basis))
            # self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis))


    def add_map_passes(self, coupling_list):
        if coupling_list is not None:              
            coupling_map = CouplingMap(couplinglist=coupling_list)
            self.pass_manager.append(SpectralMapping(coupling_list))
            self.pass_manager.append(SabreLayout(coupling_map=coupling_map))
            self.add_local_passes(1)

    def run(self, circuits, coupling_list=None, is_qrack=False):
        out_circuits = circuits
        if is_qrack:
            if isinstance(circuits, list):
                out_circuits = []
                for c in circuits:
                    opt_circuit = QrackCircuit.in_from_qiskit_circuit(c)
                    opt_circuit = opt_circuit.to_qiskit_circuit()
                    opt_circuit = transpile(opt_circuit, optimization_level=0, basis_gates=self.target_basis)
                    out_circuits.append(opt_circuit)
            else:
                out_circuits = QrackCircuit.in_from_qiskit_circuit(circuits)
                out_circuits = out_circuits.to_qiskit_circuit()
                out_circuits = transpile(out_circuits, optimization_level=0, basis_gates=self.target_basis)

        self.add_map_passes(coupling_list)
        out_circuits = self.pass_manager.run(out_circuits)

        return out_circuits

