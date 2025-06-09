from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import Target, CouplingMap
import numpy as np


class DeviceNoiseProfile:
    """
    A container for a device's noise and topology characteristics.
    """

    def __init__(self, target: Target):
        if not isinstance(target, Target):
            raise TypeError("Input must be a Qiskit Target instance.")

        # self.target = get_target(target) # Temporarily disable if causing issues
        self.target = target
        self.coupling_map = self.target.build_coupling_map()
        self.cnot_errors = {}
        self.swap_costs = {}
        self.readout_errors = {}
        self._build_noise_model()

    def _get_operation_error(self, op_name, qubits):
        """A generic helper to safely get error for any operation."""
        try:
            props = self.target[op_name][qubits]
            if props and props.error is not None:
                return props.error
            # Return a default high error if not specified
            return 0.1
        except (KeyError, AttributeError):
            # Return a default high error if gate/qubits not found
            return 0.1

    def _build_noise_model(self):
        if not self.coupling_map:
            return

        # --- THE DEFINITIVE FIX IS HERE ---
        # Iterate through the qubits and get the error of the 'measure' op on each
        for q_idx in range(self.target.num_qubits):
            # Qubits for single-qubit ops are specified as a tuple, e.g., (0,)
            self.readout_errors[q_idx] = self._get_operation_error(
                "measure", (q_idx,)
            )

        for q1, q2 in self.coupling_map.get_edges():
            self.cnot_errors[(q1, q2)] = self._get_operation_error(
                "cx", (q1, q2)
            )

            fid_cx12 = 1.0 - self.cnot_errors.get((q1, q2), 0.1)
            # We need the error for the reverse CNOT for the SWAP cost
            fid_cx21 = 1.0 - self._get_operation_error("cx", (q2, q1))

            swap_fidelity = fid_cx12 * fid_cx21 * fid_cx12
            self.swap_costs[(q1, q2)] = 1.0 - swap_fidelity
            self.swap_costs[(q2, q1)] = 1.0 - swap_fidelity

    def get_correction_rules(self):
        """Returns a placeholder dictionary of correction rules."""
        return {}

    def get_hardware_vector(self) -> list[float]:
        """
        Calculates a fixed-length vector summarizing the device's noise.
        """
        cnot_errors_list = list(self.cnot_errors.values())
        if not cnot_errors_list:
            avg_cnot_error = 0.1
            std_cnot_error = 0.0
        else:
            avg_cnot_error = np.mean(cnot_errors_list)
            std_cnot_error = np.std(cnot_errors_list)

        readout_errors_list = list(self.readout_errors.values())
        if not readout_errors_list:
            avg_readout_error = 0.1
        else:
            avg_readout_error = np.mean(readout_errors_list)

        # --- THE FIX IS HERE ---
        # Explicitly cast each numpy float to a standard Python float.
        # This makes the list JSON serializable.
        return [
            float(avg_cnot_error),
            float(std_cnot_error),
            float(avg_readout_error),
        ]

    def get_t1_t2(self, qubit: int) -> tuple[float, float]:
        """Safely gets T1 and T2 times for a qubit."""
        try:
            # NOTE: The exact access path depends on the Qiskit version and backend object.
            # This is for a modern `target` object.
            if not isinstance(qubit, int):
                qubit = (
                    qubit.index
                )  # or use another method to derive the index
            t1 = self.target.qubit_properties[qubit].t1
            t2 = self.target.qubit_properties[qubit].t2
            return (t1, t2)
        except (AttributeError, IndexError):
            # Return a very poor default value if data is missing
            return (0.0, 0.0)

    def get_readout_error(self, qubit: int) -> float:
        """Safely gets readout error for a qubit."""
        return self.readout_errors.get(qubit, 1.0)  # Default to max error

    def get_gate_properties(
        self, op_name: str, qubits: tuple
    ) -> tuple[float, float]:
        """Safely gets error and duration for a given gate on specific qubits."""
        try:
            props = self.target[op_name][qubits]
            error = props.error if (props and props.error is not None) else 1.0
            duration = (
                props.duration
                if (props and props.duration is not None)
                else 0.0
            )
            return (error, duration)
        except (KeyError, AttributeError):
            # Return a very poor default value if gate/qubits not supported
            return (1.0, 0.0)


class ResourcePruningPass(TransformationPass):
    """
    Filters out noisy qubits and couplings before layout and routing.
    """

    def __init__(
        self,
        device_profile: DeviceNoiseProfile,
        readout_threshold=0.05,
        cnot_threshold=0.01,
    ):
        super().__init__()
        self.profile = device_profile
        self.readout_threshold = readout_threshold
        self.cnot_threshold = cnot_threshold

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        original_map = self.profile.coupling_map
        if not original_map:
            return dag

        good_qubits = {
            q
            for q, error in self.profile.readout_errors.items()
            if error < self.readout_threshold
        }

        good_edges = [
            (q1, q2)
            for (q1, q2), error in self.profile.cnot_errors.items()
            if q1 in good_qubits
            and q2 in good_qubits
            and error < self.cnot_threshold
        ]

        pruned_map = CouplingMap(good_edges)
        self.property_set["coupling_map"] = pruned_map
        return dag
