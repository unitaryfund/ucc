"""Default Qiskit pass-manager configuration used by the compiler.

This module wraps a preset or locally assembled Qiskit pass manager and exposes
the small API used by ``ucc.compile``.
"""

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
    """Build and run the default UCC compilation pass manager.

    Attributes:
        DEFAULT_GATESET: Fallback basis gate set used when no backend or custom
            gateset is supplied.
        pass_manager: The configured Qiskit pass manager.
        target_backend: Optional backend used to derive the target basis set.
        target_gateset: The basis-gate set used for synthesis and translation.
    """

    DEFAULT_GATESET = {"cx", "rz", "rx", "ry", "h"}

    def __init__(
        self,
        local_iterations: int = 1,
        target_backend: Optional[Backend] = None,
        target_gateset: Optional[set] = None,
    ):
        """Initialize the compiler configuration.

        Args:
            local_iterations: Number of times to run the local optimization
                pass block.
            target_backend: Optional backend used to derive the target basis
                gate set.
            target_gateset: Optional explicit basis-gate set.

        Raises:
            ValueError: If the backend does not expose a target operation set.

        Notes:
            If neither ``target_backend`` nor ``target_gateset`` resolve to a
            gateset, the default basis ``{"cx", "rz", "rx", "ry", "h"}``
            is used.
        """
        self.pass_manager = PassManager()
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

    @property
    def default_passes(self):
        """Return the default pass sequence placeholder."""
        return

    def _add_local_passes(self, local_iterations):
        """Append the local optimization passes to the pass manager.

        Args:
            local_iterations: Number of times to repeat the local pass block.
        """
        for _ in range(local_iterations):
            self.pass_manager.append(Optimize1qGatesDecomposition())
            self.pass_manager.append(CommutativeCancellation())
            self.pass_manager.append(Collect2qBlocks())
            self.pass_manager.append(ConsolidateBlocks(force_consolidate=True))
            self.pass_manager.append(
                UnitarySynthesis(basis_gates=self.target_gateset)
            )
            # self.pass_manager.append(Optimize1qGatesDecomposition(basis=self._1q_basis))
            self.pass_manager.append(CollectCliffords())
            self.pass_manager.append(
                HighLevelSynthesis(hls_config=HLSConfig(clifford=["greedy"]))
            )

            # Add following passes if merging single qubit rotations that are interrupted by a commuting 2 qubit gate is desired
            # self.pass_manager.append(Optimize1qGatesSimpleCommutation(basis=self._1q_basis))

    def run(self, circuits, callback=None):
        """Run the configured pass manager on a circuit or list of circuits.

        Args:
            circuits: Circuit or list of circuits to transpile.
            callback: Optional callback invoked after each pass execution.

        Returns:
            The compiled circuit or circuit list, matching Qiskit's pass-manager
            return behavior.
        """
        return self.pass_manager.run(circuits, callback=callback)


def _get_trial_count(default_trials=5):
    """Return the number of SABRE trials to use.

    Args:
        default_trials: Fallback trial count when all-thread execution is not
            enabled.

    Returns:
        The default trial count or the number of available processes when
        Qiskit is configured to use all threads.
    """
    if CONFIG.get("sabre_all_threads", None) or os.getenv(
        "QISKIT_SABRE_ALL_THREADS"
    ):
        return default_num_processes()
    return default_trials
