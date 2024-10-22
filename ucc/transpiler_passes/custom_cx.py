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


from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.quantum_info import Operator
from qiskit.quantum_info.operators.predicates import matrix_equal
 
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
        op2,
        ) -> bool:
        """Checks whether two operators ``op1`` and ``op2`` commute with one another."""
        is_commuting = False
        qargs1 = op1.qargs
        if not op1.is_standard_gate():
                op1 = op1.op
        qargs2 = op2.qargs
        if not op2.is_standard_gate():
                op2 = op2.op
        if set(qargs1).isdisjoint(qargs2):
            is_commuting = True
        elif op1.name == "cx": 
            if op2.name == "cx":
                is_commuting = ((qargs1[0] == qargs2[0]) or (qargs1[1] == qargs2[1]))
            elif op2.name == "rx":
                is_commuting = (qargs1[1] == qargs2[0])
            elif op2.name == "rz":
                is_commuting = (qargs1[0] == qargs2[0])
        elif op1.name == "rx":
            if op2.name == "cx":
                is_commuting = (qargs1[0] == qargs2[1])
        elif op1.name == "rz":
            if op2.name == "cx":
                is_commuting = (qargs1[0] == qargs2[0])
        return is_commuting


    def _is_inverse(self, node1, node2):
        """Checks whether two nodes ``node1`` and ``node2`` are inverses of one
        another and act on the same quibts."""
        phase_difference = 0
        mat1 = Operator(node1.op.inverse()).data
        mat2 = Operator(node2.op).data
        props = {}
        is_inverse = matrix_equal(mat1, mat2, ignore_phase=True, props=props)
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


    def _remove_cancelling_nodes(self, idx, node_list, dag):
        dag._multi_graph.remove_node_retain_edges_by_id(node_list[idx]._node_id)
        self._decrement_cx_op(dag, node_list[idx].name) # update dictionary of node names
        return dag


    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """
        Execute checks for commutation and inverse cancellation on the DAG.
        Remove pairs of nodes which cancel one another.
        """
        new_dag = copy(dag)
        topo_sorted_nodes = list(new_dag.topological_op_nodes())
        remove_nodes = [False] * len(topo_sorted_nodes)
        phase_update = 0
        for i in range(len(topo_sorted_nodes)):
            matched_j = -1
            for j in range(i - 1, -1, -1):
                if remove_nodes[j]:
                    continue
                if (topo_sorted_nodes[j].qargs == topo_sorted_nodes[i].qargs
                    and topo_sorted_nodes[j].cargs == topo_sorted_nodes[i].cargs
                ):
                    is_inverse, phase = self._is_inverse(topo_sorted_nodes[i], topo_sorted_nodes[j])
                    if is_inverse:
                        phase_update += phase
                        matched_j = j
                        break
                if not (self._is_commuting(topo_sorted_nodes[i], topo_sorted_nodes[j])):
                    break
            if matched_j != -1:
                remove_nodes[i] = True
                remove_nodes[matched_j] = True
        for idx in range(len(topo_sorted_nodes)):
            if remove_nodes[idx]:
                self._remove_cancelling_nodes(idx, topo_sorted_nodes, new_dag)
        if phase_update != 0:
            dag.global_phase += phase_update

        return new_dag
