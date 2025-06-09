# In your file, e.g., ucc/noise_aware/ml_router.py

import torch
import math
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler import TranspilerError
from qiskit.dagcircuit import DAGCircuit
from qiskit.circuit.library import SwapGate
from torch.cuda.amp import autocast
from qiskit.transpiler import Layout

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
