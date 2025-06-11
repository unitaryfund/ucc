#!/usr/bin/env python
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import Target, CouplingMap
import numpy as np
import argparse
import json
from tqdm import tqdm

from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps
from qiskit.converters import circuit_to_dag
from qiskit_ibm_runtime.fake_provider import FakeWashingtonV2
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit.synthesis import QDrift

# Import structured circuit generators
from qiskit.circuit.library import QFT, EfficientSU2, QuantumVolume

import torch
import math
from qiskit.transpiler import TranspilerError
from qiskit.circuit.library import SwapGate
from torch.cuda.amp import autocast
from qiskit.transpiler import Layout


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


# Assume these classes will be created in other files
# from ucc.noise_aware import CircuitFormer


class MLFidelityRouter(TransformationPass):
    """
    An AI-driven routing pass that uses a Transformer model to predict the fidelity
    of different routing decisions, guided by just-in-time calibration data.
    """

    def __init__(
        self, target, model, noise_profile, max_seq_len: int, config=None
    ):
        super().__init__()
        self.target = target
        self.model = model
        self.noise_profile = noise_profile
        self.coupling_map = target.build_coupling_map()
        # NOTE: Use shortest_undirected_path as it's the correct method name
        # self.dist_matrix is a numpy array, the method is on coupling_map
        # We will use coupling_map directly later.
        self.dist_matrix = self.coupling_map.distance_matrix

        self.config = config or {}
        self.candidate_top_k = self.config.get("candidate_top_k", 5)

        # Ensure the model is in evaluation mode
        if self.model:
            self.model.eval()

        # --- Configuration for the Feature Extractor ---
        self.GATE_VOCAB = ["cx", "sx", "rz", "x", "id", "measure", "other"]
        self.NUM_PARAMS = 1
        self.NUM_QUBIT_FEATURES = 3
        self.NUM_GATE_CAL_FEATURES = 2
        self.FEATURE_DIM = (
            len(self.GATE_VOCAB)
            + self.NUM_PARAMS
            + self.NUM_QUBIT_FEATURES * 2
            + self.NUM_GATE_CAL_FEATURES
        )  # Total should be 16

        # Maximum circuit length (in gates) to consider
        self.MAX_LEN = max_seq_len

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        if (
            "layout" not in self.property_set
            or self.property_set["layout"] is None
        ):
            raise TranspilerError(
                "MLFidelityRouter requires a layout to be set."
            )

        layout = self.property_set["layout"]

        while dag.op_nodes():
            self._apply_runnable_gates(dag, layout)

            gates_to_route = self._get_unroutable_front_layer(dag, layout)

            if not gates_to_route:
                break

            # --- Step 1: Generate a few good CANDIDATE SEQUENCES ---
            candidate_sequences = self._generate_candidate_swap_sequences(
                gates_to_route, layout, num_candidates=self.candidate_top_k
            )

            if not candidate_sequences:
                raise TranspilerError(
                    "Heuristic could not find any SWAP sequences to resolve the circuit."
                )

            # --- Step 2: Use the AI to evaluate each candidate sequence ---
            best_sequence = None
            best_fidelity = -1.0

            for seq in candidate_sequences:
                # Create a temporary state to simulate the outcome of applying the sequence
                temp_dag = dag.copy_empty_like()
                temp_dag.compose(dag)
                temp_layout = layout.copy()

                # Apply the entire sequence to the temporary state
                for swap in seq:
                    self._apply_swap(temp_dag, temp_layout, swap)

                # Convert the potential final state into a feature tensor
                feature_tensor = self._dag_to_feature_tensor(
                    temp_dag, temp_layout
                )

                # Get the AI's prediction for this sequence
                predicted_fidelity = self._evaluate_single_state_with_ai(
                    feature_tensor
                )

                # --- Step 3: Keep track of the best one found so far ---
                if predicted_fidelity > best_fidelity:
                    best_fidelity = predicted_fidelity
                    best_sequence = seq

            # --- Step 4: Apply ONLY the winning sequence to the real DAG ---
            if best_sequence:
                for swap in best_sequence:
                    self._apply_swap(dag, layout, swap)
            else:
                # Fallback in case of a bug or no valid sequences
                raise TranspilerError(
                    "AI evaluation failed to select a best SWAP sequence."
                )

        self.property_set["layout"] = layout
        return dag

    def _is_physically_connected(self, p_q0: int, p_q1: int) -> bool:
        """
        A robust, custom method to check if two physical qubits are connected.
        It checks for the edge in both directions.
        """
        return (p_q0, p_q1) in self.coupling_map.get_edges() or (
            p_q1,
            p_q0,
        ) in self.coupling_map.get_edges()

    def _generate_candidate_swap_sequences(
        self, gates_to_route, layout, num_candidates=3
    ):
        """
        For the unroutable gates, generate a few distinct, plausible SWAP sequences.
        """
        candidate_sequences = []

        # We will generate one sequence for each of the first few unroutable gates
        for gate_node in gates_to_route[:num_candidates]:
            p_q0, p_q1 = layout[gate_node.qargs[0]], layout[gate_node.qargs[1]]

            # Find the shortest path of physical qubits
            path = self.coupling_map.shortest_undirected_path(p_q0, p_q1)

            # Convert the path into a sequence of SWAP operations
            # A simple path is just a sequence of swaps along the chain
            swap_sequence = []
            # The path includes the start and end, so we iterate up to len-1
            for i in range(len(path) - 1):
                # The swap is between the current node and the next node in the path
                swap_qubits = tuple(sorted((path[i], path[i + 1])))
                swap_sequence.append(swap_qubits)

            if swap_sequence:
                candidate_sequences.append(swap_sequence)

        # Return a list of lists of swaps
        return candidate_sequences

    def _apply_runnable_gates(self, dag: DAGCircuit, layout: Layout):
        """
        Iteratively finds and removes any gates in the front layer that are
        executable with the current layout, simplifying the DAG.
        """
        while True:
            # Find all gates in the current front layer
            front_layer_nodes = list(dag.front_layer())

            # If the front layer is empty, we're done
            if not front_layer_nodes:
                break

            made_progress = False
            for node in front_layer_nodes:
                # 1-qubit gates are always runnable
                if node.op.num_qubits == 1:
                    dag.remove_op_node(node)
                    made_progress = True
                    continue

                # For 2-qubit gates, check connectivity
                if node.op.num_qubits == 2:
                    v_q0, v_q1 = node.qargs
                    p_q0, p_q1 = layout[v_q0], layout[v_q1]

                    # If the physical qubits are connected, the gate is runnable
                    if self._is_physically_connected(p_q0, p_q1):
                        dag.remove_op_node(node)
                        made_progress = True

            # If we went through the whole front layer and couldn't run any gates,
            # it means the remaining gates are all unroutable. We stop.
            if not made_progress:
                break

    def _apply_swap(self, dag, layout, swap_qubits):
        """Helper to apply a single SWAP to both DAG and layout."""
        p_q1, p_q2 = swap_qubits
        v_q1 = layout._p2v.get(p_q1)
        v_q2 = layout._p2v.get(p_q2)
        if v_q1 is not None and v_q2 is not None:
            dag.apply_operation_back(SwapGate(), qargs=(v_q1, v_q2))
        layout.swap(p_q1, p_q2)

    def _get_unroutable_front_layer(self, dag, layout):
        """Finds all gates in the current front layer that can't be run."""
        unroutable = []
        for node in dag.front_layer():
            if node.op.num_qubits == 2:
                p0, p1 = layout[node.qargs[0]], layout[node.qargs[1]]

                if self._is_physically_connected(p0, p1):
                    unroutable.append(node)
        return unroutable

    def _find_best_heuristic_swap_sequence(self, gate_to_route, layout):
        """Uses a simple heuristic to find a sequence of SWAPs to resolve a gate."""
        p_q0, p_q1 = (
            layout[gate_to_route.qargs[0]],
            layout[gate_to_route.qargs[1]],
        )

        # Find the shortest path of physical qubits
        path = self.coupling_map.shortest_undirected_path(p_q0, p_q1)

        # Convert the path into a sequence of SWAP operations
        swap_sequence = []
        for i in range(len(path) - 2):
            swap_sequence.append(tuple(sorted((path[i], path[i + 1]))))

        return swap_sequence

    def _evaluate_single_state_with_ai(self, feature_tensor):
        """Uses the AI model to predict the fidelity of a single circuit state."""
        model_device = next(self.model.parameters()).device

        # Add a batch dimension of 1
        input_tensor = feature_tensor.unsqueeze(0).to(model_device)

        with torch.no_grad(), autocast():
            prediction = self.model(input_tensor)

        return prediction.item()

    def _dag_to_feature_tensor(
        self, dag: DAGCircuit, v2p_mapping: dict
    ) -> torch.Tensor:
        """
        The "Feature Extractor". Converts a DAGCircuit into a tensor representation
        for the CircuitFormer model.

        For each gate, it creates a rich feature vector containing information about
        the gate's type, parameters, and the JIT calibration data of the
        physical qubits it acts upon.

        Args:
            dag: The circuit's DAG representation.
            v2p_mapping (dict): The final virtual-to-physical qubit mapping dictionary.

        Returns:
            A PyTorch tensor of shape [self.MAX_LEN, self.FEATURE_DIM].
        """
        gate_feature_sequence = []

        # Iterate through all operations in a topological order
        for node in dag.op_nodes():
            # --- 1. Gate Type Encoding (One-Hot) ---
            gate_type_encoding = [0.0] * len(self.GATE_VOCAB)
            op_name = node.op.name
            if op_name in self.GATE_VOCAB:
                gate_type_encoding[self.GATE_VOCAB.index(op_name)] = 1.0
            else:
                gate_type_encoding[-1] = 1.0  # 'other' category

            # --- 2. Gate Parameter Encoding ---
            gate_params = [0.0] * self.NUM_PARAMS
            if hasattr(node.op, "params") and node.op.params:
                # Normalize angle to be in [-0.5, 0.5] for better ML stability
                gate_params[0] = float(node.op.params[0]) / (2 * math.pi)

            # --- 3. Physical Qubit and Gate Calibration Features ---
            phys_q1_features = [0.0] * self.NUM_QUBIT_FEATURES
            phys_q2_features = [0.0] * self.NUM_QUBIT_FEATURES
            gate_cal_features = [0.0] * self.NUM_GATE_CAL_FEATURES

            p_qubits = []
            for vq in node.qargs:
                if vq in v2p_mapping:
                    p_qubits.append(v2p_mapping[vq])

            if p_qubits:
                pq1 = p_qubits[0]
                # Get features for the first physical qubit
                t1, t2 = self.noise_profile.get_t1_t2(pq1)
                readout_err = self.noise_profile.get_readout_error(pq1)
                phys_q1_features = [t1, t2, readout_err]

                if len(p_qubits) == 2:
                    # It's a 2-qubit gate
                    pq2 = p_qubits[1]
                    t1, t2 = self.noise_profile.get_t1_t2(pq2)
                    readout_err = self.noise_profile.get_readout_error(pq2)
                    phys_q2_features = [t1, t2, readout_err]

                    gate_err, gate_dur = (
                        self.noise_profile.get_gate_properties(
                            op_name, (pq1, pq2)
                        )
                    )
                    gate_cal_features = [gate_err, gate_dur]
                else:
                    # It's a 1-qubit gate
                    gate_err, gate_dur = (
                        self.noise_profile.get_gate_properties(op_name, (pq1,))
                    )
                    gate_cal_features = [gate_err, gate_dur]

            # --- 4. Assemble the Final Feature Vector ---
            feature_vector = (
                gate_type_encoding
                + gate_params
                + phys_q1_features
                + phys_q2_features
                + gate_cal_features
            )
            gate_feature_sequence.append(feature_vector)

        # --- 5. Padding and Truncation ---
        # Truncate if longer than MAX_LEN
        truncated_sequence = gate_feature_sequence[: self.MAX_LEN]

        # 2. Pad the sequence with zero vectors if it's too short
        padded_sequence = truncated_sequence
        padding_needed = self.MAX_LEN - len(padded_sequence)

        if padding_needed > 0:
            # self.FEATURE_DIM is correctly accessed as a class attribute
            zero_vector = [0.0] * self.FEATURE_DIM
            padded_sequence.extend([zero_vector] * padding_needed)

        # --- 6. Convert to PyTorch Tensor ---
        return torch.tensor(padded_sequence, dtype=torch.float32)


# --- HELPER FUNCTIONS ---

# --- CIRCUIT GENERATOR PORTFOLIO ---


def create_random_circuit(num_qubits: int, num_gates: int) -> QuantumCircuit:
    """Creates a circuit with random CNOTs and single-qubit gates."""
    qc = QuantumCircuit(num_qubits)
    rng = np.random.default_rng(seed=num_qubits + num_gates)
    for _ in range(num_gates):
        if num_qubits > 1 and rng.random() > 0.3:
            q1, q2 = rng.choice(num_qubits, 2, replace=False)
            qc.cx(q1, q2)
        else:
            q = rng.integers(num_qubits)
            gate_type = rng.choice(["sx", "x", "rz"])
            if gate_type == "rz":
                angle = rng.uniform(0, 2 * math.pi)
                qc.rz(angle, q)
            else:
                getattr(qc, gate_type)(q)
    return qc


def create_qft_circuit(num_qubits: int) -> QuantumCircuit:
    """Creates a QFT circuit, excellent for testing routing and structured dependencies."""
    return QFT(num_qubits, do_swaps=False, approximation_degree=0).decompose()


def create_ansatz_circuit(num_qubits: int) -> QuantumCircuit:
    """Creates a VQE-style ansatz circuit with variable depth."""
    reps = np.random.randint(1, 4)  # Randomize the depth (1 to 3 repetitions)
    return EfficientSU2(num_qubits, reps=reps).decompose()


def create_quantum_volume_circuit(num_qubits: int) -> QuantumCircuit:
    """Creates a Quantum Volume circuit, designed to stress compilers with all-to-all mixing."""
    # Quantum Volume is defined for depth=qubits
    return QuantumVolume(num_qubits, depth=num_qubits, seed=42).decompose()


def create_heisenberg_circuit(
    rows: int, cols: int, trotter_steps: int = 1
) -> QuantumCircuit:
    """
    Creates a circuit for simulating the Heisenberg spin model on a 2D square lattice.

    The Heisenberg Hamiltonian is H = J * Σ (X_i X_j + Y_i Y_j + Z_i Z_j) over all
    neighboring <i,j> pairs. This function sets the coupling strength J=1 and simulation time t=1.

    Args:
        rows: The number of rows in the square lattice.
        cols: The number of columns in the square lattice.
        trotter_steps: The number of Trotter steps for the time evolution simulation.
                       Higher steps mean a more accurate but deeper circuit.

    Returns:
        A QuantumCircuit object representing the time evolution, decomposed into
        basis gates (CNOTs and single-qubit rotations).
    """
    num_qubits = rows * cols
    if num_qubits <= 1:
        # Return an empty circuit if the lattice is too small for interactions
        return QuantumCircuit(num_qubits)

    # 1. Define the interactions (Hamiltonian terms) using Pauli strings
    pauli_list = []

    # Helper function to map (row, col) coordinates to a single qubit index
    def get_qubit_idx(r, c):
        return r * cols + c

    # Iterate over all qubits in the grid to define neighbor interactions
    for r in range(rows):
        for c in range(cols):
            # Interaction with the neighbor to the right (Horizontal)
            if c < cols - 1:
                idx1, idx2 = get_qubit_idx(r, c), get_qubit_idx(r, c + 1)
                # Ensure idx1 > idx2 for consistent Pauli string generation
                if idx1 < idx2:
                    idx1, idx2 = idx2, idx1

                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}X{'I' * (idx1 - idx2 - 1)}X{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Y{'I' * (idx1 - idx2 - 1)}Y{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Z{'I' * (idx1 - idx2 - 1)}Z{'I' * idx2}",
                        1.0,
                    )
                )

            # Interaction with the neighbor below (Vertical)
            if r < rows - 1:
                idx1, idx2 = get_qubit_idx(r, c), get_qubit_idx(r + 1, c)
                if idx1 < idx2:
                    idx1, idx2 = idx2, idx1

                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}X{'I' * (idx1 - idx2 - 1)}X{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Y{'I' * (idx1 - idx2 - 1)}Y{'I' * idx2}",
                        1.0,
                    )
                )
                pauli_list.append(
                    (
                        f"{'I' * (num_qubits - idx1 - 1)}Z{'I' * (idx1 - idx2 - 1)}Z{'I' * idx2}",
                        1.0,
                    )
                )

    if not pauli_list:
        return QuantumCircuit(num_qubits)

    # 2. Create the Hamiltonian operator from the list of Pauli strings
    hamiltonian = SparsePauliOp.from_list(pauli_list)

    # 3. Use a Trotterization method to create the evolution circuit.
    # We use QDrift, a simple first-order method. The `reps` argument
    # corresponds to the number of Trotter steps.
    qdrift = QDrift(reps=trotter_steps)

    # Synthesize the operator into a gate representing e^(-iHt) where t=1
    evolution_gate = qdrift.synthesize(hamiltonian)

    # 4. Wrap the synthesized evolution into a QuantumCircuit
    qc = QuantumCircuit(num_qubits, name=f"heisenberg_{rows}x{cols}")
    qc.append(evolution_gate, range(num_qubits))

    # Decompose the high-level evolution gate into CNOTs and single-qubit gates
    return qc.decompose()


def create_qcnn_circuit(num_qubits: int) -> QuantumCircuit:
    """
    Creates a Quantum Convolutional Neural Network (QCNN) circuit.

    This implements a common QCNN architecture with alternating convolutional
    and pooling layers, reducing the number of active qubits by half at each
    pooling step. The circuit is fully parameterized.

    Args:
        num_qubits: The number of input qubits. Must be a power of 2.

    Returns:
        A QuantumCircuit object representing the QCNN.

    Raises:
        ValueError: If the number of qubits is not a power of 2.
    """
    if not (num_qubits > 0 and (num_qubits & (num_qubits - 1) == 0)):
        raise ValueError("Number of qubits for QCNN must be a power of 2.")

    qc = QuantumCircuit(num_qubits, name=f"qcnn_{num_qubits}q")

    # --- Helper function for a two-qubit convolutional unit ---
    def conv_unit(params: list) -> QuantumCircuit:
        """A single parameterized 2-qubit convolutional filter."""
        # This is a standard, entangling two-qubit unitary.
        # It requires 5 parameters.
        target = QuantumCircuit(2)
        target.rz(params[0], 0)
        target.rz(params[1], 1)
        target.crx(
            params[2], 0, 1
        )  # Controlled-RX is a good entangling choice
        target.ry(params[3], 0)
        target.ry(params[4], 1)
        return target

    active_qubits = list(range(num_qubits))
    param_idx = 0

    # The hierarchical structure continues until only one qubit remains "active"
    while len(active_qubits) > 1:
        # --- 1. Convolutional Layer ---
        # Apply convolutional units to adjacent pairs of active qubits
        for i in range(0, len(active_qubits), 2):
            q1, q2 = active_qubits[i], active_qubits[i + 1]

            # Create 5 new parameters for this specific unit
            conv_params = [Parameter(f"p_{param_idx + j}") for j in range(5)]
            param_idx += 5

            conv_gate = conv_unit(conv_params).to_gate(label="Conv")
            qc.append(conv_gate, [q1, q2])

        qc.barrier()

        # --- 2. Pooling Layer ---
        # Apply a CNOT and effectively discard the target qubit for the next layer
        next_active_qubits = []
        for i in range(0, len(active_qubits), 2):
            q_control = active_qubits[i]
            q_target = active_qubits[i + 1]
            qc.cx(q_control, q_target)

            # The control qubit moves on to the next layer
            next_active_qubits.append(q_control)

        active_qubits = next_active_qubits
        if len(active_qubits) > 1:
            qc.barrier()

    return qc


# --- DATA PROCESSING LOGIC (Unchanged from before) ---
def calculate_fidelity_label(
    circuit: QuantumCircuit,
    v2p_mapping: dict,
    noise_profile: DeviceNoiseProfile,
) -> float:
    fidelity = 1.0
    for instruction in circuit.data:
        if instruction.operation.name == "cx":
            v_q1, v_q2 = instruction.qubits
            # Check if both virtual qubits are in our mapping before proceeding
            if v_q1 in v2p_mapping and v_q2 in v2p_mapping:
                p_q1, p_q2 = v2p_mapping[v_q1], v2p_mapping[v_q2]
                error, _ = noise_profile.get_gate_properties(
                    "cx", (p_q1, p_q2)
                )
                fidelity *= 1.0 - error
    return fidelity


def process_circuit(
    circuit: QuantumCircuit, backend, router_instance: MLFidelityRouter
):
    try:
        transpiled_circuit = transpile(
            circuit, backend=backend, optimization_level=3, seed_transpiler=42
        )
    except TranspilerError:
        return None

    if (
        not hasattr(transpiled_circuit, "layout")
        or transpiled_circuit.layout is None
    ):
        return None
    final_v2p_mapping = transpiled_circuit.layout.final_virtual_layout()
    dag = circuit_to_dag(transpiled_circuit)

    fidelity = calculate_fidelity_label(
        transpiled_circuit, final_v2p_mapping, router_instance.noise_profile
    )
    feature_tensor = router_instance._dag_to_feature_tensor(
        dag, final_v2p_mapping
    )

    qasm_string = str(dumps(transpiled_circuit))

    return {
        "fidelity_label": fidelity,
        "feature_tensor": feature_tensor.tolist(),
        "final_qasm": qasm_string,
        "circuit_type": circuit.name,
    }


# --- MAIN EXECUTION BLOCK ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a diverse fidelity dataset for the CircuitFormer model."
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=5000,
        help="Total number of circuits to generate.",
    )
    parser.add_argument(
        "--max-qubits",
        type=int,
        default=15,
        help="Maximum number of qubits for generated circuits.",
    )
    parser.add_argument(
        "--min-qubits",
        type=int,
        default=4,
        help="Minimum number of qubits for generated circuits.",
    )
    parser.add_argument(
        "--max-seq-len",
        type=str,
        default=512,
        help="same size with model_seq_len",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="diverse_fidelity_dataset.json",
        help="Name of the output JSON file.",
    )
    args = parser.parse_args()

    print("--- Initializing Backend and Noise Models ---")
    backend = FakeWashingtonV2()
    noise_profile = DeviceNoiseProfile(backend.target)
    print(
        f"Initialized with backend: {backend.name} ({backend.num_qubits} qubits)"
    )

    router_for_feature_extraction = MLFidelityRouter(
        backend.target,
        model=None,
        noise_profile=noise_profile,
        max_seq_len=args.max_seq_len,
    )
    print(
        f"Feature vector dimension is set to: {router_for_feature_extraction.FEATURE_DIM}"
    )

    # --- The "Recipe" for Our Dataset ---
    # We define a portfolio of generators and the probability of choosing each one.
    # This ensures a diverse mix of circuit types.
    circuit_generators = {
        "random": (create_random_circuit, 0.10),  # 10% chance
        "qft": (create_qft_circuit, 0.30),  # 30% chance
        "ansatz": (create_ansatz_circuit, 0.25),  # 25% chance
        "qv": (create_quantum_volume_circuit, 0.1),  # 10% chance
        "qcnn": (create_qcnn_circuit, 0.15),  # 20% chance
        "heisenberg": (create_heisenberg_circuit, 0.10),  # 15% chance
    }
    generator_names, generator_params = zip(*circuit_generators.items())
    generator_funcs, generator_weights = zip(*generator_params)

    dataset = []
    print(
        f"\n--- Generating {args.num_samples} Data Samples from Diverse Portfolio ---"
    )

    master_rng = np.random.default_rng(seed=42)

    for _ in tqdm(range(args.num_samples), desc="Generating Circuits"):
        generator_name = master_rng.choice(
            generator_names, p=generator_weights
        )
        generator_func = circuit_generators[generator_name][0]

        if generator_name == "heisenberg":
            # Generate a random square-ish lattice
            rows = master_rng.integers(2, 6)
            cols = master_rng.integers(2, 6)
            num_qubits = rows * cols
            if num_qubits > args.max_qubits:
                continue  # Skip if too large
            trotter_steps = master_rng.integers(1, 4)
            raw_circuit = generator_func(rows, cols, trotter_steps)
            raw_circuit.name = f"heisenberg_{rows}x{cols}_{trotter_steps}steps"

        elif generator_name == "qcnn":
            # QCNNs need a number of qubits that is a power of 2
            possible_qubit_counts = [4, 8, 16, 32, 64]
            valid_qubit_counts = [
                q
                for q in possible_qubit_counts
                if args.min_qubits <= q <= args.max_qubits
            ]
            if not valid_qubit_counts:
                continue  # Skip if no valid sizes
            num_qubits = master_rng.choice(valid_qubit_counts)
            raw_circuit = generator_func(num_qubits)
            raw_circuit.name = f"qcnn_{num_qubits}q"

        else:
            num_qubits = master_rng.integers(
                args.min_qubits, args.max_qubits + 1
            )
            if generator_name == "random":
                num_gates = master_rng.integers(num_qubits, num_qubits * 5)
                raw_circuit = generator_func(num_qubits, num_gates)
                raw_circuit.name = f"random_{num_qubits}q_{num_gates}g"
            else:
                raw_circuit = generator_func(num_qubits)
                raw_circuit.name = f"{generator_name}_{num_qubits}q"

        if raw_circuit.num_parameters > 0:
            # This circuit is a template. We need to fill in concrete values.
            # Generate random values for each parameter.
            param_values = master_rng.uniform(
                0, 2 * np.pi, raw_circuit.num_parameters
            )

            # The `parameters` attribute is an ordered set of the Parameter objects.
            # We create a dictionary mapping them to our random values.
            binding_map = dict(zip(raw_circuit.parameters, param_values))

            # `assign_parameters` returns a new, concrete circuit with the values baked in.
            raw_circuit = raw_circuit.assign_parameters(binding_map)

        # 4. Process the circuit to get our data point
        processed_data = process_circuit(
            raw_circuit, backend, router_for_feature_extraction
        )

        if processed_data:
            dataset.append(processed_data)

    # Save the complete dataset to a file
    with open(args.output_file, "w") as f:
        json.dump(dataset, f, indent=2)

    print("\n--- Dataset Generation Complete ---")
    print(f"Successfully created {len(dataset)} samples.")
    print(f"Saved to '{args.output_file}'")

    import re
    from collections import Counter

    # Use regex to split on '-' or '_'
    circuit_types = [re.split("[-_]", d["circuit_type"])[0] for d in dataset]
    print("\nDataset Composition:")
    for name, count in Counter(circuit_types).items():
        # Increase precision if needed
        print(
            f"- {name}: {count} samples ({(count / len(dataset) * 100):.1f}%)"
        )
