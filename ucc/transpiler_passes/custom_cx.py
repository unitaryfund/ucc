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
from qiskit.circuit.operation import Operation
from qiskit.circuit import Qubit
from qiskit.quantum_info import Operator
from qiskit.quantum_info.operators.predicates import matrix_equal
 
from typing import List

class CXCancellation(TransformationPass):
    """
    Cancel redundant CX gates by checking each connected pair of DAG nodes
    against simple commutation rules, as presented in
    https://www.aspdac.com/aspdac2019/archive/pdf/2D-2.pdf.
    """
 
    def __init__(self):
        super().__init__()


    def commute(
        self,
        op1: Operation,
        qargs1: List[Qubit],
        op2: Operation,
        qargs2: List[Qubit],
        ) -> bool:
        """Checks whether two operators ``op1`` and ``op2`` commute with one another."""
        commuting = False 
        if op1.name == "cx": 
            if op2.name == "cx":
                commuting = (qargs1[0] == qargs2[0] or qargs1[1] == qargs2[1]) or (qargs1[0] != qargs2[0] and qargs1[1] != qargs2[1])
            elif op2.name == "rx":
                commuting = (qargs1[1] == qargs2[0]) or (qargs2[0] not in (qargs1[0], qargs1[1]))
            elif op2.name == "rz":
                commuting = (qargs1[0] == qargs2[0]) or (qargs2[0] not in (qargs1[0], qargs1[1]))
        elif op1.name == "rx":
            if op2.name == "cx":
                commuting = (qargs1[0] == qargs2[1]) or (qargs1[0] not in (qargs2[0], qargs2[1]))
        elif op1.name == "rz":
            if op2.name == "cx":
                commuting = (qargs1[0] == qargs2[0]) or (qargs1[0] not in (qargs2[0], qargs2[1]))
        return commuting


    def _check_inverse(self, node1, node2):
        """Checks whether two nodes ``node1`` and ``node2`` are inverses of one another."""
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


    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """
        Execute checks for commutation and inverse cancellation on the DAG.
        Remove pairs of nodes which cancel one another.
        """
        topo_sorted_nodes = list(dag.topological_op_nodes())
        for i, node1 in enumerate(topo_sorted_nodes[:-1]):
            node2 = topo_sorted_nodes[i+1]
            is_inverse, phase_update = self._check_inverse(node1, node2)
            if is_inverse:
                dag._multi_graph.remove_node_retain_edges_by_id(node1._node_id)
                self._decrement_cx_op(dag, node1.name)
                dag._multi_graph.remove_node_retain_edges_by_id(node2._node_id)
                self._decrement_cx_op(dag, node2.name)
                dag.global_phase += phase_update
            elif self.commute(
                    node1.op,
                    node1.qargs,
                    node2.op,
                    node2.qargs
                    ):
                    if i < len(topo_sorted_nodes) - 3:
                        node_pairs = [(topo_sorted_nodes[i-1], node2), (node1, topo_sorted_nodes[i+2])]
                    else:
                        node_pairs = [(topo_sorted_nodes[i-1], node2)] # avoid checking a node out of range 
                    for n1, n2 in node_pairs:
                        is_inverse, phase_update = self._check_inverse(n1, n2)
                        if is_inverse:
                            dag._multi_graph.remove_node_retain_edges_by_id(n1._node_id)
                            self._decrement_cx_op(dag, n1.name)
                            dag._multi_graph.remove_node_retain_edges_by_id(n2._node_id)
                            self._decrement_cx_op(dag, n2.name)
                            dag.global_phase += phase_update  
        return dag

