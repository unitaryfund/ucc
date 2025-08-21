# Construct a custom compiler
import os

try:
    from qiskit.utils.parallel import default_num_processes
except ImportError:
    # Qiskit 1.0.0 doesn't have this function, so we make it ourselves
    from qiskit.utils.parallel import CPU_COUNT

    def default_num_processes():
        return CPU_COUNT


from qiskit.transpiler import PassManager
from qiskit import user_config
from qiskit.transpiler import Target
from qiskit.transpiler.passes import (
    ApplyLayout,
    ConsolidateBlocks,
    CollectCliffords,
    HighLevelSynthesis,
    HLSConfig,
    SabreLayout,
    SabreSwap,
    VF2Layout,
    CommutativeCancellation,
    Collect2qBlocks,
    UnitarySynthesis,
    Optimize1qGatesDecomposition,
    VF2PostLayout,
)
from typing import Optional


CONFIG = user_config.get_config()


class UCCDefault1:
    def __init__(
        self,
        local_iterations: int = 1,
        target_device: Optional[Target] = None,
        target_gateset: Optional[set] = None,
    ):
        """
        Create a new instance of UCCDefault1 compiler

            Args:
                local_iterations (int): Number of times to run the local passes
                target_device (qiskit.transpiler.Target): (Optional) The target device to compile the circuit for
        """
        self.pass_manager = PassManager()
        self.target_device = target_device
        self.target_gateset = target_gateset
        self._add_local_passes(local_iterations)
        self._add_map_passes(target_device)

    @property
    def default_passes(self):
        return

    @property
    def target_basis(self):
        # Use the target device's gateset if available, otherwise use the provided gateset, otherwise
        if hasattr(self.target_device, "operation_names"):
            # Use target_device gateset if available
            target_gateset = self.target_device.operation_names
        elif self.target_gateset is not None:
            # Use provided gateset if available
            target_gateset = self.target_gateset
        else:
            # Default if no target device or gateset is provided
            target_gateset = {"cx", "rz", "rx", "ry", "h"}

        return target_gateset

    def _add_local_passes(self, local_iterations):
        for _ in range(local_iterations):
            self.pass_manager.append(Optimize1qGatesDecomposition())
            self.pass_manager.append(CommutativeCancellation())
            self.pass_manager.append(Collect2qBlocks())
            self.pass_manager.append(ConsolidateBlocks(force_consolidate=True))
            self.pass_manager.append(
                UnitarySynthesis(basis_gates=self.target_basis)
            )
            # self.pass_manager.append(Optimize1qGatesDecomposition(basis=self._1q_basis))
            self.pass_manager.append(CollectCliffords())
            self.pass_manager.append(
                HighLevelSynthesis(hls_config=HLSConfig(clifford=["greedy"]))
            )

            # Add following passes if merging single qubit rotations that are interrupted by a commuting 2 qubit gate is desired
            # self.pass_manager.append(Optimize1qGatesSimpleCommutation(basis=self._1q_basis))

    def _add_map_passes(self, target_device: Optional[Target] = None):
        if target_device is not None:
            coupling_map = target_device.build_coupling_map()
            # self.pass_manager.append(ElidePermutations())
            # self.pass_manager.append(SpectralMapping(coupling_list))
            # self.pass_manager.append(SetLayout(pass_manager_config.initial_layout))
            self.pass_manager.append(
                SabreLayout(
                    coupling_map,
                    seed=1,
                    max_iterations=4,
                    swap_trials=_get_trial_count(20),
                    layout_trials=_get_trial_count(20),
                )
            )

            self.pass_manager.append(VF2Layout(target=target_device))
            self.pass_manager.append(ApplyLayout())
            self.pass_manager.append(
                SabreSwap(
                    coupling_map,
                    heuristic="decay",
                    seed=1,
                    trials=_get_trial_count(20),
                )
            )
            # self.pass_manager.append(MapomaticLayout(coupling_map))
            self.pass_manager.append(VF2PostLayout(target=target_device))
            self.pass_manager.append(ApplyLayout())
            self._add_local_passes(1)
            self.pass_manager.append(VF2PostLayout(target=target_device))
            self.pass_manager.append(ApplyLayout())

    def run(self, circuits):
        return self.pass_manager.run(circuits)


def _get_trial_count(default_trials=5):
    if CONFIG.get("sabre_all_threads", None) or os.getenv(
        "QISKIT_SABRE_ALL_THREADS"
    ):
        return default_num_processes()
    return default_trials
