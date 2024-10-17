# This file is a derivative work from similar transpiler passes in Qiskit. 
# 
# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


from cmath import phase
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.quantum_info import Operator
from qiskit.quantum_info.operators.predicates import matrix_equal
from qiskit.dagcircuit.exceptions import DAGCircuitError
 
from copy import copy

class CXCancellation(TransformationPass):
    """
    Cancel redundant CX gates by checking each connected pair of DAG nodes
    against simple commutation rules, as presented in
    https://www.aspdac.com/aspdac2019/archive/pdf/2D-2.pdf.
    """
 
    def __init__(self):
        super().__init__()

    def _is_commuting(
        self,
        op1,
        qargs1,
        op2,
        qargs2,
        ) -> bool:
        """Checks whether two operators ``op1`` and ``op2`` commute with one another."""
        commuting = False 
        if op1.name == "cx": 
            if op2.name == "cx":
                commuting = (qargs1[0] == qargs2[0] or qargs1[1] == qargs2[1])
            elif op2.name == "rx":
                commuting = (qargs1[1] == qargs2[0])
            elif op2.name == "rz":
                commuting = (qargs1[0] == qargs2[0])
        elif op1.name == "rx":
            if op2.name == "cx":
                commuting = (qargs1[0] == qargs2[1])
        elif op1.name == "rz":
            if op2.name == "cx":
                commuting = (qargs1[0] == qargs2[0])
        return commuting


    def _is_connected(self, dag, node1, node2):
        try:
            dag._multi_graph.get_all_edge_data(node1._node_id, node2._node_id)
            connected = True
        except:
            connected = False
        return connected


    def _inverse_gates(self, node1, node2):
        """Checks whether two nodes ``node1`` and ``node2`` are inverses of one
        another and whether they are connected."""
        phase_difference = 0
        mat1 = Operator(node1.op.inverse()).data
        mat2 = Operator(node2.op).data
        props = {}

        is_inverse = matrix_equal(mat1, mat2, ignore_phase=True, props=props) and node1.qargs == node2.qargs
        if is_inverse:
            phase_difference = props["phase_difference"]
        return is_inverse, phase_difference


    def _decrement_cx_op(self, dag, op_name):
        """
        Remove the name associated with the removed CX gate from the
        dictionary containing the names of nodes in the DAG.
        """
        if dag._op_names[op_name] == 'cx':
            del dag._op_names[op_name]
        else:
            dag._op_names[op_name] -= 1


    def _remove_cancelling_nodes(self, dag, node1, node2, phase_update):
        dag._multi_graph.remove_node_retain_edges_by_id(node1._node_id)
        self._decrement_cx_op(dag, node1.name) # update dictionary of node names
        dag._multi_graph.remove_node_retain_edges_by_id(node2._node_id)
        self._decrement_cx_op(dag, node2.name) # update dictionary of node names
        dag.global_phase += phase_update
        return dag

    
    def _select_node_indices(index, num_nodes):
        if index == 0: # avoid checking nodes out of range
            idxs = [(index + 1, index + 2)]
        elif 0 < index < num_nodes - 3:
            # check for inverses to the left of the first node and to the right of the second
            idxs = [(index - 1, index), (index + 1, index + 2)]
        else:
            idxs = [(index - 1, index)] # avoid checking a node out of range
            return idxs

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """
        Execute checks for commutation and inverse cancellation on the DAG.
        Remove pairs of nodes which cancel one another.
        """
        new_dag = copy(dag)
        topo_sorted_nodes = list(new_dag.topological_op_nodes())
        remove_nodes = [False] * len(topo_sorted_nodes)
        phase_update_list = [0] * len(topo_sorted_nodes)
        for i in range(len(topo_sorted_nodes[:-1])):
            if remove_nodes[i] or remove_nodes[i + 1]:
                continue
            else:
                node1 = topo_sorted_nodes[i]
                node2 = topo_sorted_nodes[i+1]
                remove, phase = self._inverse_gates(node1, node2)
                if remove:
                    remove_nodes[i : i + 2] = [remove] * 2
                    phase_update_list[i] = phase
                elif self._is_commuting(node1.op, node1.qargs, node2.op, node2.qargs):
                    # Swap commuting and connected pairs of nodes 
                    try:
                        new_dag.swap_nodes(node1, node2)
                        topo_sorted_nodes[i] = node2
                        topo_sorted_nodes[i+1] = node1 
                        idxs = self._select_node_indices(i, len(topo_sorted_nodes))
                        # check if each node pair is inverse
                        for idx1, idx2 in idxs:
                            remove, phase = self._inverse_gates(topo_sorted_nodes[idx1], topo_sorted_nodes[idx2]) 
                            if remove:
                                remove_nodes[idx1 : idx2 + 1] = [remove] * 2                       
                                phase_update_list[idx1] = phase
                    except: # skip nodes that are not connected
                        pass
                if i > len(topo_sorted_nodes) - 3:
                    break
        
        for r, remove_node in enumerate(remove_nodes):
            if remove_node:
                new_dag._multi_graph.remove_node_retain_edges_by_id(topo_sorted_nodes[r]._node_id)
                self._decrement_cx_op(new_dag, topo_sorted_nodes[r].name) # update dictionary of node names
        
        dag.global_phase += sum(phase_update_list)

        return new_dag
