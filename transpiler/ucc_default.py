#Construct a custom compiler
from qiskit.transpiler import PassManager
from qiskit.compiler import transpile
from qiskit.transpiler.passes import BasisTranslator, Optimize1qGates, ConsolidateBlocks, Collect2qBlocks, Collect1qRuns
from qiskit.transpiler.passes import Collect2qBlocks, CommutativeInverseCancellation, CommutativeCancellation
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel

# from ucc_passes.entanglement_net_to_layout import Decompose2qNetworkWithMap

class UCCDefault1:
    def __init__(self, local_iterations=1):
        self.pass_manager = PassManager()
        self.target_basis = ['rz', 'rx', 'ry', 'h', 'cx']
        self.special_commutations = {
            ("rx", "cx"): {
                (0,): False,
                (1,): True,
            },
        }
        self.add_local_passes(local_iterations)
        #self.add_cx_network_optimization()



    def add_local_passes(self, local_iterations):
        for _ in range(local_iterations):            
            self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis))            
            # self.pass_manager.append(Optimize1qGates())
            # self.pass_manager.append(CommutationAnalysis())
            self.pass_manager.append(CommutativeCancellation(standard_gates=self.target_basis, special_commutations=self.special_commutations))
    
    def add_map_passes(self, coupling_map = None):
        # self.pass_manager.append(Collect1qRuns())
        self.pass_manager.append(Collect2qBlocks())
        self.pass_manager.append(ConsolidateBlocks(force_consolidate=True))
        # self.pass_manager.append(Decompose2qNetworkWithMap(coupling_map))

    def run(self, circuits, coupling_map=None):
        self.add_map_passes(coupling_map)
        out_circuits = self.pass_manager.run(circuits)
        return out_circuits




