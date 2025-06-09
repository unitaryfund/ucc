# In your file, e.g., ucc/noise_aware/ml_router.py

import torch
import math
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler import TranspilerError
from qiskit.dagcircuit import DAGCircuit
from qiskit.circuit.library import SwapGate

# Assume these classes will be created in other files
# from ucc.noise_aware import CircuitFormer


class MLFidelityRouter(TransformationPass):
    """
    An AI-driven routing pass that uses a Transformer model to predict the fidelity
    of different routing decisions, guided by just-in-time calibration data.
    """

    def __init__(self, target, model, noise_profile, config=None):
        super().__init__()
        self.target = target
        self.model = model
        self.noise_profile = noise_profile
        self.coupling_map = target.build_coupling_map()
        self.dist_matrix = self.coupling_map.distance_matrix

        self.config = config or {}
        self.candidate_top_k = self.config.get("candidate_top_k", 5)

        # Ensure the model is in evaluation mode
        if self.model:
            self.model.eval()

        # --- Configuration for the Feature Extractor ---
        self.GATE_VOCAB = ["cx", "sx", "rz", "x", "id", "measure", "other"]
        self.NUM_PARAMS = 1  # We will encode one gate parameter (for RZ)
        self.NUM_QUBIT_FEATURES = 3  # T1, T2, Readout Error
        self.NUM_GATE_CAL_FEATURES = 2  # Gate Error, Gate Duration

        self.FEATURE_DIM = (
            len(self.GATE_VOCAB)
            + self.NUM_PARAMS
            + self.NUM_QUBIT_FEATURES * 2  # For two potential qubits
            + self.NUM_GATE_CAL_FEATURES
        )  # Total should be 16

        # Maximum circuit length (in gates) to consider
        self.MAX_LEN = self.config.get("max_len", 512)

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        if (
            "layout" not in self.property_set
            or self.property_set["layout"] is None
        ):
            raise TranspilerError(
                "MLFidelityRouter requires a layout to be set in the property_set."
            )

        layout = self.property_set["layout"]

        while True:
            gates_to_route = []
            for node in dag.two_qubit_ops():
                q0, q1 = node.qargs
                p0, p1 = layout[q0], layout[q1]
                if self.dist_matrix[p0, p1] > 1:
                    gates_to_route.append(node)

            if not gates_to_route:
                break

            candidate_moves = self._generate_candidates(gates_to_route, layout)

            if not candidate_moves:
                raise TranspilerError(
                    "Could not find any candidate SWAPs to resolve the circuit."
                )

            predicted_fidelities = self._evaluate_candidates_with_ai(
                dag, layout, candidate_moves
            )

            if not predicted_fidelities:
                # Fallback in case the model fails or all candidates are invalid
                best_move = candidate_moves[0]
            else:
                best_move = max(
                    predicted_fidelities, key=predicted_fidelities.get
                )

            move_type, qubits = best_move
            if move_type == "swap":
                p_q1, p_q2 = qubits
                v_q1, v_q2 = layout.inverse[p_q1], layout.inverse[p_q2]
                dag.apply_operation_back(SwapGate(), qargs=[v_q1, v_q2])
                layout.swap(p_q1, p_q2)
            # Add logic for BRIDGE gates here if needed

        self.property_set["layout"] = layout
        return dag

    def _generate_candidates(self, gates_to_route, layout):
        """
        Generates a small list of promising SWAP candidates.
        This is our "Heuristic Candidate Generator".
        """
        occupied_physicals = set(layout.get_physical_bits().values())

        # Consider all SWAPs on edges connecting occupied qubits
        possible_swaps = [
            edge
            for edge in self.coupling_map.get_edges()
            if edge[0] in occupied_physicals and edge[1] in occupied_physicals
        ]

        scored_swaps = []
        for swap in possible_swaps:
            p1, p2 = swap

            # Calculate total distance *before* the swap
            dist_before = sum(
                self.dist_matrix[layout[g.qargs[0]], layout[g.qargs[1]]]
                for g in gates_to_route
            )

            # Calculate total distance *after* the swap
            temp_layout = layout.copy()
            temp_layout.swap(p1, p2)
            dist_after = sum(
                self.dist_matrix[
                    temp_layout[g.qargs[0]], temp_layout[g.qargs[1]]
                ]
                for g in gates_to_route
            )

            score = dist_before - dist_after  # We want to maximize this score
            scored_swaps.append((score, swap))

        # Sort by the score in descending order (best improvement first)
        scored_swaps.sort(key=lambda x: x[0], reverse=True)

        # Return the top k candidates, formatted as our move tuple
        top_k_swaps = [
            ("swap", swap)
            for score, swap in scored_swaps[: self.candidate_top_k]
        ]

        return top_k_swaps

    def _evaluate_candidates_with_ai(
        self, current_dag, current_layout, candidate_moves
    ):
        """
        Uses the AI model to predict the final circuit fidelity for each candidate move.
        """
        predictions = {}
        batch_input = []
        # Prepare the input for each candidate move
        for move in candidate_moves:
            temp_dag = current_dag.copy_empty_like()
            temp_dag.compose(current_dag)
            temp_layout = current_layout.copy()

            move_type, qubits = move
            if move_type == "swap":
                p_q1, p_q2 = qubits
                v_q1, v_q2 = (
                    temp_layout.inverse[p_q1],
                    temp_layout.inverse[p_q2],
                )
                temp_dag.apply_operation_back(SwapGate(), qargs=[v_q1, v_q2])
                temp_layout.swap(p_q1, p_q2)

            # Generate the feature tensor for this potential new state
            feature_tensor = self._dag_to_feature_tensor(temp_dag, temp_layout)
            batch_input.append(feature_tensor)

        # The model evaluates all candidates at once for efficiency
        if batch_input:
            # Stack individual tensors into a single batch tensor
            batch_tensor = torch.stack(batch_input)

            with torch.no_grad():
                # Get the batch of predictions from the model
                fidelity_predictions = self.model(batch_tensor)

            # Map predictions back to their corresponding moves
            for i, move in enumerate(candidate_moves):
                predictions[move] = fidelity_predictions[i].item()

        return predictions

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
                t1, t2 = self.noise_profile.get_t1_t2(pq1._index)
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
        padded_sequence = gate_feature_sequence[: self.MAX_LEN]

        # Pad with zeros if shorter
        padding_needed = self.MAX_LEN - len(padded_sequence)
        if padding_needed > 0:
            zero_vector = [0.0] * self.FEATURE_DIM
            padded_sequence.extend([zero_vector] * padding_needed)

        # --- 6. Convert to PyTorch Tensor ---
        return torch.tensor(padded_sequence, dtype=torch.float32)
