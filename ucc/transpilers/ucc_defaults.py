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
                target_gateset (set[str]): (Optional) The gateset to compile the circuit to. e.g. {"cx", "rx",...}. `target_device` takes precedence if it provides a basis gateset.

        If neither target_device or target_gateset resolve to a gateset, defaults to {"cx", "rz", "rx", "ry", "h"}.

        """
        self.pass_manager = PassManager()
        self.target_device = target_device

        if hasattr(self.target_device, "operation_names"):
            # Use target_device gateset if available
            self.target_gateset = self.target_device.operation_names
        elif target_gateset is not None:
            # Use provided gateset if available
            self.target_gateset = target_gateset
        else:
            # Default if no target device or gateset is provided
            self.target_gateset = {"cx", "rz", "rx", "ry", "h"}

        self._add_local_passes(local_iterations)
        self._add_map_passes(target_device)

    @property
    def default_passes(self):
        return

    def _add_local_passes(self, local_iterations):
        for _ in range(local_iterations):
            self.pass_manager.append(Optimize1qGatesDecomposition())
            self.pass_manager.append(CommutativeCancellation())
            self.pass_manager.append(Collect2qBlocks())
            self.pass_manager.append(ConsolidateBlocks(force_consolidate=True))
            self.pass_manager.append(
                UnitarySynthesis(basis_gates=self.target_gateset)
            )
            self.pass_manager.append(CollectCliffords())
            self.pass_manager.append(
                HighLevelSynthesis(hls_config=HLSConfig(clifford=["greedy"]))
            )

    def _add_map_passes(self, target_device: Optional[Target] = None):
        if target_device is not None:
            print("We have a target device")
            coupling_map = target_device.build_coupling_map()
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
            self._add_local_passes(1)

    def run(self, circuits, callback=None):
        """
        Run the pass manager on the given circuit(s).

            Args:
                circuits (QuantumCircuit or list[QuantumCircuit]): Circuit(s) to transpile
                callback: A callback function that will be called after each pass execution. The
                function will be called with 5 keyword arguments::

                    pass_ (Pass): the pass being run
                    dag (DAGCircuit): the dag output of the pass
                    time (float): the time to execute the pass
                    property_set (PropertySet): the property set
                    count (int): the index for the pass execution
        """
        return self.pass_manager.run(circuits, callback=callback)


def _get_trial_count(default_trials=5):
    if CONFIG.get("sabre_all_threads", None) or os.getenv(
        "QISKIT_SABRE_ALL_THREADS"
    ):
        return default_num_processes()
    return default_trials
