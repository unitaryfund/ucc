# Construct a custom compiler
import os

try:
    from qiskit.utils.parallel import default_num_processes
except ImportError:
    # Qiskit 1.0.0 doesn't have this function, so we make it ourselves
    from qiskit.utils.parallel import CPU_COUNT

    def default_num_processes():
        return CPU_COUNT


from qiskit.providers import Backend
from qiskit.transpiler import PassManager
from qiskit import user_config
from qiskit.transpiler import generate_preset_pass_manager
from qiskit.transpiler.passes import (
    ConsolidateBlocks,
    CollectCliffords,
    HighLevelSynthesis,
    HLSConfig,
    CommutativeCancellation,
    Collect2qBlocks,
    UnitarySynthesis,
    Optimize1qGatesDecomposition,
)
from typing import Optional


CONFIG = user_config.get_config()


class UCCDefault1:
    DEFAULT_GATESET = {"cx", "rz", "rx", "ry", "h"}

    def __init__(
        self,
        local_iterations: int = 1,
        target_backend: Optional[Backend] = None,
        target_gateset: Optional[set] = None,
    ):
        """
        Create a new instance of UCCDefault1 compiler

            Args:
                local_iterations (int): Number of times to run the local passes
                target_backend (qiskit.providers.Backend): (Optional) The       target backend device to compile the circuit for
                target_gateset (set[str]): (Optional) The gateset to compile the circuit to. e.g. {"cx", "rx",...}. `target_backend` takes precedence if it provides a basis gateset.

        If neither target_backend or target_gateset resolve to a gateset, defaults to {"cx", "rz", "rx", "ry", "h"}.

        """
        self.pass_manager = PassManager()
        self._default_passes = ()
        self.target_backend = target_backend

        if self.target_backend is None:
            # If no backend is provided, use the provided gateset or default gateset
            self.target_gateset = (
                target_gateset
                if target_gateset is not None
                else self.DEFAULT_GATESET
            )
        elif hasattr(self.target_backend, "target") and hasattr(
            self.target_backend.target, "operation_names"
        ):
            # If a backend is provided, use its target's operation names as the gateset
            self.target_gateset = self.target_backend.target.operation_names
        else:
            raise ValueError(
                "Provided backend does not provide a target with operation names"
            )

        if self.target_backend is None:
            self._add_local_passes(local_iterations)
        else:
            self.pass_manager = generate_preset_pass_manager(
                optimization_level=3, backend=self.target_backend
            )
            self._default_passes = tuple(
                getattr(self.pass_manager, stage)
                for stage in self.pass_manager.stages
                if getattr(self.pass_manager, stage) is not None
            )

    @property
    def default_passes(self):
        """Return the default compilation workflow as an immutable sequence."""

        return self._default_passes

    def _add_local_passes(self, local_iterations):
        default_passes = []
        for _ in range(local_iterations):
            default_passes.extend(
                [
                    Optimize1qGatesDecomposition(),
                    CommutativeCancellation(),
                    Collect2qBlocks(),
                    ConsolidateBlocks(force_consolidate=True),
                    UnitarySynthesis(basis_gates=self.target_gateset),
                    CollectCliffords(),
                    HighLevelSynthesis(
                        hls_config=HLSConfig(clifford=["greedy"])
                    ),
                ]
            )
            # self.pass_manager.append(Optimize1qGatesDecomposition(basis=self._1q_basis))
            # Add following passes if merging single qubit rotations that are interrupted by a commuting 2 qubit gate is desired
            # self.pass_manager.append(Optimize1qGatesSimpleCommutation(basis=self._1q_basis))

        self._default_passes = tuple(default_passes)
        self.pass_manager.append(list(self._default_passes))

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
