#Construct a custom compiler
from qiskit.transpiler import PassManager
from qiskit.compiler import transpile
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
from qiskit.transpiler import CouplingMap

from ..transpiler_passes import BasisTranslator, CommutativeCancellation, Collect2qBlocks, ConsolidateBlocks, UnitarySynthesis, Optimize1qGatesDecomposition
from ..transpiler_passes import SpectralMapping, SabreLayout




# from ucc_passes.entanglement_net_to_layout import Decompose2qNetworkWithMap

class UCCDefault1:
    def __init__(self, local_iterations=1):
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
        self.add_local_passes(local_iterations)
        #self.add_cx_network_optimization()

    def add_local_passes(self, local_iterations):
        for _ in range(local_iterations):            
            self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis))            
            self.pass_manager.append(Optimize1qGatesDecomposition())
            self.pass_manager.append(CommutativeCancellation(standard_gates=self.target_basis, special_commutations=self.special_commutations))
            self.pass_manager.append(Collect2qBlocks())
            self.pass_manager.append(ConsolidateBlocks())
            self.pass_manager.append(UnitarySynthesis(basis_gates=self.target_basis))
            self.pass_manager.append(Optimize1qGatesDecomposition(basis=self._1q_basis))            
    
    def add_map_passes(self, coupling_list = None):
        if coupling_list is not None:              
            coupling_map = CouplingMap(couplinglist=coupling_list)
            self.pass_manager.append(SpectralMapping(coupling_list))
            self.pass_manager.append(SabreLayout(coupling_map=coupling_map))
            self.add_local_passes(1)

    def run(self, circuits, coupling_list=None):
        self.add_map_passes(coupling_list)
        out_circuits = self.pass_manager.run(circuits)
        return out_circuits




