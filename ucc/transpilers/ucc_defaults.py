#Construct a custom compiler
import os
from qiskit.utils.parallel import CPU_COUNT
from qiskit.transpiler import PassManager
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary as sel
from qiskit import user_config
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import (
    BasisTranslator,
    ConsolidateBlocks,
    CollectCliffords,
    HighLevelSynthesis,
    HLSConfig,
    SabreLayout,
    SabreSwap,
    BasicSwap,
    LookaheadSwap,
    StochasticSwap,
)
from qiskit.transpiler.passes.synthesis.unitary_synthesis import DefaultUnitarySynthesis
# from ucc.transpiler_passes.sabre_swap import SabreSwap
from ucc.transpiler_passes.py2qan_plugin import Py2QAN_Routing

from ..transpiler_passes import  CommutativeCancellation, Collect2qBlocks, UnitarySynthesis, Optimize1qGatesDecomposition, CXCancellation, SpectralMapping

from qiskit.transpiler.passes import Optimize1qGatesSimpleCommutation, ElidePermutations


CONFIG = user_config.get_config()


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

    @property
    def default_passes(self):
        return 
        
    def add_local_passes(self, local_iterations):
        for _ in range(local_iterations):            
            self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis))            
            self.pass_manager.append(Optimize1qGatesDecomposition())
            self.pass_manager.append(CommutativeCancellation(standard_gates=self.target_basis, special_commutations=self.special_commutations))
            self.pass_manager.append(Collect2qBlocks())
            self.pass_manager.append(ConsolidateBlocks(force_consolidate=True))
            self.pass_manager.append(UnitarySynthesis(basis_gates=self.target_basis))
            # self.pass_manager.append(Optimize1qGatesDecomposition(basis=self._1q_basis))
            self.pass_manager.append(CollectCliffords())
            self.pass_manager.append(HighLevelSynthesis(hls_config=HLSConfig(clifford=["greedy"])))
            self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis)) 

            #Add following passes if merging single qubit rotations that are interrupted by a commuting 2 qubit gate is desired
            # self.pass_manager.append(Optimize1qGatesSimpleCommutation(basis=self._1q_basis))
            # self.pass_manager.append(BasisTranslator(sel, target_basis=self.target_basis)) 
            
    
    def add_map_passes(self, coupling_list = None):
        if coupling_list is not None:              
            coupling_map = CouplingMap(couplinglist=coupling_list)
            # self.pass_manager.append(ElidePermutations())
            # self.pass_manager.append(SpectralMapping(coupling_list))
            # self.pass_manager.append(SetLayout(pass_manager_config.initial_layout))
            # self.pass_manager.append(
            #    SabreLayout(
            #       coupling_map,
            #       max_iterations=4,
            #       swap_trials=_get_trial_count(20),
            #       layout_trials=_get_trial_count(20),
            #    )
            # )
            # self.pass_manager.append(
            #     SabreSwap(
            #         coupling_map,
            #         heuristic="decay",
            #         trials=_get_trial_count(20),
            #     )
            # )
            self.pass_manager.append(Py2QAN_Routing(coupling_map=coupling_map))
            self.add_local_passes(1)

    def run(self, circuits, coupling_list=None):
        self.add_map_passes(coupling_list)
        out_circuits = self.pass_manager.run(circuits)
        return out_circuits


def _get_trial_count(default_trials=5):
    if CONFIG.get("sabre_all_threads", None) or os.getenv("QISKIT_SABRE_ALL_THREADS"):
        return max(CPU_COUNT, default_trials)
    return default_trials

