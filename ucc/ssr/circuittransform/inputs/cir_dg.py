# -*- coding: utf-8 -*-
"""
Created on Wed Oct 13 22:22:04 2021

This module is last modified on 1/11/2021

@author: zhoux
"""

from qiskit import QuantumCircuit, QuantumRegister
import networkx as nx
from networkx.algorithms import approximation as approx
from networkx import DiGraph
from math import pi


from ucc.ssr.circuittransform.inputs.gate_info import (
    supported_gate_names,
    gate_depth_cx,
)
from ucc.ssr.circuittransform.front_circuit import FrontCircuit


def add_gate_to_qiskit_cir(cir, gate):
    name = gate[0]
    q = gate[1]
    p = gate[2]
    if len(q) > 2:
        raise ()
    if name not in supported_gate_names:
        raise (Exception("Unsupported gate {}".format(name)))
    if name == "cx":
        cir.cx(q[0], q[1])
    if name == "cz":
        cir.cz(q[0], q[1])
    if name == "swap":
        cir.swap(q[0], q[1])
    if name == "h":
        cir.h(q[0])
    if name == "s":
        cir.s(q[0])
    if name == "t":
        cir.t(q[0])
    if name == "x":
        cir.x(q[0])
    if name == "y":
        cir.y(q[0])
    if name == "z":
        cir.z(q[0])
    if name == "id":
        cir.id(q[0])
    if name == "p":
        cir.p(p[0], q[0])
    if name == "rx":
        cir.rx(p[0], q[0])
    if name == "ry":
        cir.ry(p[0], q[0])
    if name == "rz":
        cir.rz(p[0], q[0])
    if name == "u1":
        # cir.u1(p[0], q[0])
        cir.p(p[0], q[0])
    if name == "u2":
        # cir.u2(p[0], p[1], q[0])
        cir.u(pi / 2, p[0], p[1], q[0])
    if name == "u3" or name == "u":
        cir.u(p[0], p[1], p[2], q[0])
    if name == "tdg":
        cir.tdg(q[0])
    if name == "sx":
        cir.sx(q[0])


def CreateCircuitFromQASM(file, path=None):
    if path == None:
        path = "D:/data/QASM example/"

    QASM_file = open(path + file, "r")
    iter_f = iter(QASM_file)
    QASM = ""
    for line in iter_f:
        QASM = QASM + line
    cir = QuantumCircuit.from_qasm_str(QASM)
    QASM_file.close

    return cir


class DG(DiGraph):
    def __init__(self, basic_2_q_gate="cx"):
        super().__init__()
        self.qubit_to_node = [None] * 500
        self.num_gate_2q = 0
        self.num_gate_1q = 0
        self.node_count = 0
        self.num_q = 0
        self.basic_2_q_gate = basic_2_q_gate
        if self.basic_2_q_gate == "cx":
            self.gate_depth = gate_depth_cx
        else:
            raise (
                Exception(f"Unsupported 2-qubit gate type {basic_2_q_gate}.")
            )

    #### Get attributes
    @property
    def num_gate(self):
        return self.num_gate_1q + self.num_gate_2q

    def get_node_count(self, num_q=None):
        """
        Return the node number. If num_q is not None, then we only count nodes
        with num_q qubits.
        """
        if num_q == None:
            return len(self.nodes)
        count = 0
        for node in self.nodes:
            if self.get_node_num_q(node) == num_q:
                count += 1
        return count

    def num_block(self, num_q):
        """The number of blocks (nodes) with num_q qubits"""
        count = 0
        for node in self.nodes:
            if self.get_node_num_q(node) == num_q:
                count += 1
        return count

    def get_shared_qubits(self, node1, node2):
        """Get qubits which exist in both node1 and node2"""
        qubits = []
        for q in self.get_node_qubits(node1):
            if q in self.get_node_qubits(node2):
                qubits.append(q)
        return qubits

    def get_node_num_gate(self, node):
        return len(self.get_node_gates(node))

    def get_node_num_q(self, node):
        return len(self.nodes[node]["qubits"])

    def get_node_num_2q_gates(self, node):
        return self.nodes[node]["num_gate_2q"]

    def get_node_num_1q_gates(self, node):
        return self.nodes[node]["num_gate_1q"]

    def get_node_gates(self, node):
        return self.nodes[node]["gates"]

    def get_node_qubits(self, node):
        return self.nodes[node]["qubits"]

    def get_node_depth(self, node):
        """One SWAP takes 3 depth."""
        qubit_depth = [0] * (max(self.get_node_qubits(node)) + 1)
        for name, qubits, _ in self.get_node_gates(node):
            current_ds = []
            for q in qubits:
                current_ds.append(qubit_depth[q])
            current_d = max(current_ds)
            if name == "SWAP" or name == "swap":
                current_d += 3
            else:
                current_d += 1
            for q in qubits:
                qubit_depth[q] = current_d
        return max(qubit_depth)

    def get_edge_qubits(self, edge):
        return self.edges[edge]["qubits"]

    def set_edge_qubits(self, edge, qubits):
        self.edges[edge]["qubits"] = list(qubits)

    #### Node and edge related operations
    def add_line(self, node_in, node_out, qubits=None, check=True):
        """
        Connect two nodes using provided qubits.
        qubits: qubits to be connected.
        """
        qubits_share = self.get_shared_qubits(node_in, node_out)
        qubits_used = []
        for edge_c in self.out_edges(node_in):
            qubits_used.extend(self.get_edge_qubits(edge_c))
        for edge_c in self.in_edges(node_out):
            qubits_used.extend(self.get_edge_qubits(edge_c))
        qubits_share_new = []
        for q in qubits_share:
            if q not in qubits_used:
                qubits_share_new.append(q)
        qubits_share = qubits_share_new

        if qubits == None:
            qubits = qubits_share
        if check:
            for q in qubits:
                if q not in qubits_share:
                    print(qubits)
                    print(qubits_share)
                    raise ()
        edge_add = (node_in, node_out)
        if edge_add in self.edges:
            for q in qubits:
                if q not in self.edges[edge_add]["qubits"]:
                    self.edges[edge_add]["qubits"].append(q)
        else:
            self.add_edge(node_in, node_out, qubits=qubits)

    def add_gate(self, gate, add_edges=True, update_dg_attrs=True):
        """
        Attributes of a node:
            gates
            num_gate_1q
            num_gate_2q
            qubits
        """
        # add node
        node_new = self.node_count
        self.node_count += 1
        self.add_node(node_new)
        self.nodes[node_new]["gates"] = [gate]
        self.nodes[node_new]["qubits"] = list(gate[1])
        (
            self.nodes[node_new]["num_gate_1q"],
            self.nodes[node_new]["num_gate_2q"],
        ) = 0, 0
        if len(gate[1]) == 1:
            self.nodes[node_new]["num_gate_1q"] += 1
            if update_dg_attrs:
                self.num_gate_1q += 1
        if len(gate[1]) == 2:
            self.nodes[node_new]["num_gate_2q"] += 1
            if update_dg_attrs:
                self.num_gate_2q += 1
        if len(gate[1]) > 2:
            raise ()
        if max(gate[1]) + 1 > self.num_q:
            self.num_q = max(gate[1]) + 1
        if add_edges:
            # add edges assuming the added gate appears at the end of the circuit
            for q in gate[1]:
                node_parent = self.qubit_to_node[q]
                if node_parent != None:
                    self.add_line(node_parent, node_new, [q])
                self.qubit_to_node[q] = node_new
        return node_new

    def add_gates(self, gates, add_edges=True, update_dg_attrs=True):
        """
        Attributes of a node:
            gates
            num_gate_1q
            num_gate_2q
            qubits
        """
        # add node
        node_new = self.node_count
        self.node_count += 1
        if node_new in self.nodes:
            raise ()
        self.add_node(node_new)
        self.nodes[node_new]["gates"] = gates
        qubits = []
        num_gate_1q, num_gate_2q = 0, 0
        for _, qs, _ in gates:
            if len(qs) == 1:
                if update_dg_attrs:
                    self.num_gate_1q += 1
                num_gate_1q += 1
            if len(qs) == 2:
                if update_dg_attrs:
                    self.num_gate_2q += 1
                num_gate_2q += 1
            if len(qs) > 2:
                raise ()
            for q in qs:
                if q not in qubits:
                    qubits.append(q)
        self.nodes[node_new]["qubits"] = qubits
        (
            self.nodes[node_new]["num_gate_1q"],
            self.nodes[node_new]["num_gate_2q"],
        ) = num_gate_1q, num_gate_2q

        # add edges
        if add_edges:
            raise (Exception("This function has not been implemented!"))
        return node_new

    def add_gate_absorb(self, gate):
        """Add a gate and absorb is if possible"""
        nodes_check = []
        for q in gate[1]:
            node_father = self.qubit_to_node[q]
            if node_father not in nodes_check and node_father != None:
                nodes_check.append(node_father)
        # add node
        new_node = self.add_gate(gate)
        # absorb
        for node_parent in nodes_check:
            if not self.check_absorbable(node_parent, new_node):
                continue
            new_node = self.cascade_node(new_node, node_parent)
        # self.check()
        return new_node

    def break_node(self, node):
        """
        Break a node to make qubits of each sub-nodes connected
        """
        qubits = self.get_node_qubits(node)
        qubit_groups = [[q] for q in qubits]
        for _, qubits, _ in self.get_node_gates(node):
            new_group = []
            for q in qubits:
                for i, qs in enumerate(qubit_groups):
                    if q in qs:
                        new_group.extend(qubit_groups.pop(i))
                        break
            qubit_groups.append(new_group)
        if len(qubit_groups) == 1:
            # if all qubits are connected, we don't break the node
            return [node]

        gate_groups = [[] for _ in range(len(qubit_groups))]
        for gate in self.get_node_gates(node):
            q = gate[1][0]
            for i, qs in enumerate(qubit_groups):
                if q in qs:
                    for q in gate[1]:
                        if q not in qs:
                            raise ()
                    gate_groups[i].append(gate)
                    break
        pre_nodes = list(self.predecessors(node))
        pre_qubits = [
            self.get_edge_qubits((pre_node, node)) for pre_node in pre_nodes
        ]
        succ_nodes = list(self.successors(node))
        succ_qubits = [
            self.get_edge_qubits((node, node_succ)) for node_succ in succ_nodes
        ]
        # delete node
        self.remove_node(node)
        # add nodes
        nodes_add = []
        for gates in gate_groups:
            nodes_add.append(
                self.add_gates(gates, add_edges=False, update_dg_attrs=False)
            )
        # add edges
        ## add incoming edges
        for node_pre, qs in zip(pre_nodes, pre_qubits):
            for node_new in nodes_add:
                qs_shared = self.get_shared_qubits(node_pre, node_new)
                edge_qubits = []
                for q in qs:
                    if q in qs_shared:
                        edge_qubits.append(q)
                if len(edge_qubits) > 0:
                    self.add_line(node_pre, node_new, qubits=edge_qubits)
        ## add outcoming edges
        for node_succ, qs in zip(succ_nodes, succ_qubits):
            for node_new in nodes_add:
                qs_shared = self.get_shared_qubits(node_succ, node_new)
                edge_qubits = []
                for q in qs:
                    if q in qs_shared:
                        edge_qubits.append(q)
                if len(edge_qubits) > 0:
                    self.add_line(node_new, node_succ, qubits=edge_qubits)
        return nodes_add

    def break_node_gates(self, node):
        """
        Break a node to make each sub node contains only one gate.
        """
        gates = [g for g in self.get_node_gates(node)]
        pre_nodes = list(self.predecessors(node))
        pre_qubit_to_node = {}
        for pre_node in pre_nodes:
            for q in self.get_edge_qubits((pre_node, node)):
                pre_qubit_to_node[q] = pre_node
        succ_nodes = list(self.successors(node))
        succ_qubit_to_node = {}
        for succ_node in succ_nodes:
            for q in self.get_edge_qubits((node, succ_node)):
                succ_qubit_to_node[q] = succ_node
        # delete node
        self.remove_node(node)
        # add nodes
        nodes_add = []
        for gate in gates:
            nodes_add.append(
                self.add_gate(gate, add_edges=False, update_dg_attrs=False)
            )
        # add edges
        ## add incoming edges
        for node_new in nodes_add:
            qubits = self.get_node_qubits(node_new)
            for q in qubits:
                node_pre = pre_qubit_to_node[q]
                self.add_line(node_pre, node_new, qubits=[q])
                pre_qubit_to_node[q] = node_new
        ## add outcoming edges
        for q, node_succ in succ_qubit_to_node.items():
            self.add_line(pre_qubit_to_node[q], node_succ, qubits=[q])
        return nodes_add

    def cascade_node(self, node1, node2):
        """
        Combine two given nodes.
        Here we only update one node (node_in) and delete the other (node_out)
        instead of creating one node and deleting both.
        """
        if not self.check_direct_dependency(node1, node2):
            if not self.check_parallel(node1, node2):
                raise ()
        if (node1, node2) in self.edges:
            node_in, node_out = node1, node2
        else:
            if (node2, node1) in self.edges:
                node_in, node_out = node2, node1
            else:
                # we accept two nodes are parallel
                node_in, node_out = node1, node2
        # update attributes
        self.nodes[node_in]["gates"].extend(self.nodes[node_out]["gates"])
        for gate in self.nodes[node_out]["gates"]:
            if len(gate[1]) == 1:
                self.nodes[node_in]["num_gate_1q"] += 1
            if len(gate[1]) == 2:
                self.nodes[node_in]["num_gate_2q"] += 1
            for q in gate[1]:
                if q not in self.nodes[node_in]["qubits"]:
                    self.nodes[node_in]["qubits"].append(q)
        # delete node and add egdes
        for node in list(self.successors(node_out)):
            self.add_line(
                node_in,
                node,
                self.get_edge_qubits((node_out, node)),
                check=False,
            )
        for node in list(self.predecessors(node_out)):
            if node != node_in:
                self.add_line(
                    node,
                    node_in,
                    self.get_edge_qubits((node, node_out)),
                    check=False,
                )
        ## update qubit_to_node
        for q in self.get_node_qubits(node_out):
            if self.qubit_to_node[q] == node_out:
                self.qubit_to_node[q] = node_in
        self.remove_node(node_out)
        # self.check()
        return node_in

    #### File import and export
    def from_qasm(self, file, path=None, absorb=True):
        qiskit_cir = CreateCircuitFromQASM(file, path)
        self.from_qiskit_circuit(qiskit_cir, absorb)

    def from_qiskit_circuit(self, qiskit_cir, absorb=True):
        """
        args:
            absorb: a node can contain multiple gates.

        """
        self.num_q = len(qiskit_cir.qregs[0])
        self.num_q_log = self.num_q
        data = qiskit_cir.data
        for qiskit_gate in data:
            name = qiskit_gate[0].name
            qargs = qiskit_gate[1]
            paras = tuple(qiskit_gate[0].params)
            qubits = []
            for qubit_qiskit in qargs:
                qubits.append(qubit_qiskit._index)
            gate = (name, tuple(qubits), paras)
            if absorb:
                self.add_gate_absorb(gate)
            else:
                self.add_gate(gate)

    def from_dg(self, dg, absorb=True):
        self.num_q = dg.num_q
        self.num_q_log = dg.num_q
        nodes_mapping = {}
        for node in nx.topological_sort(dg):
            nodes_add = []
            for gate in dg.get_node_gates(node):
                if absorb:
                    node_add = self.add_gate_absorb(gate)
                else:
                    node_add = self.add_gate(gate)
                if node_add not in nodes_add:
                    nodes_add.append(node_add)
            # we presume that no existing nodes will be removed during any
            # potential absorption
            nodes_mapping[node] = nodes_add
        return nodes_mapping

    def qiskit_circuit(
        self,
        save_to_file=False,
        add_barrier=False,
        decompose_swap=False,
        file_name="circuit",
    ):
        """Convert the DG to a qiskit circuit"""

        if decompose_swap:
            if self.basic_2_q_gate == "cx":
                from ucc.ssr.circuittransform.inputs.gate_info import (
                    gen_swap_via_cx as gen_swap,
                )
                # from gate_info import gen_swap_via_cx as gen_swap
        # init circuits
        qubits = QuantumRegister(self.num_q, "q")
        ag = nx.complete_graph(self.num_q)
        circuit = FrontCircuit(self, ag)
        cir_qiskit = QuantumCircuit(qubits)
        # print(circuit)
        # add qiskit gates one by one
        while circuit.num_remain_nodes > 0:
            front_nodes = circuit.front_layer
            if len(front_nodes) == 0:
                raise ()

            for node in front_nodes:
                gates = self.get_node_gates(node)
                for gate in gates:
                    if decompose_swap:
                        if gate[0] == "swap":
                            for gate2 in gen_swap(gate[1][0], gate[1][1]):
                                add_gate_to_qiskit_cir(cir_qiskit, gate2)
                            continue
                    add_gate_to_qiskit_cir(cir_qiskit, gate)
                if add_barrier:
                    cir_qiskit.barrier()
            circuit.execute_front_layer()
        if save_to_file:
            fig = cir_qiskit.draw(
                scale=0.7,
                filename=None,
                style=None,
                output="mpl",
                interactive=False,
                plot_barriers=True,
                reverse_bits=False,
            )
            fig.savefig(file_name + ".svg", format="svg")
        return cir_qiskit

    def to_qasm(self, file_name="cir.qasm", add_measurement=False):
        cir = self.qiskit_circuit()
        if add_measurement:
            from qiskit import ClassicalRegister

            c = ClassicalRegister(len(cir.qubits), "c")
            cir.add_register(c)
            cir.measure(cir.qregs[0], c)
        # cir.qasm(filename=file_name)
        # modified by yq
        from qiskit.qasm2.export import dumps

        qasm_code = dumps(cir)
        with open(file_name, "w") as file:
            file.write(qasm_code)

    #### Data structure based operations

    def get_unitary(self, num_q=None, swaps=[]):
        print("get unitary")
        from circuittransform.front_circuit import FrontCircuit
        from qiskit import transpile
        from qiskit_aer import AerSimulator

        if num_q == None:
            num_q = self.num_q
        backend = AerSimulator()
        q = QuantumRegister(num_q, "q")
        cir_qiskit = QuantumCircuit(q)
        ag = nx.complete_graph(self.num_q)
        circuit = FrontCircuit(self, ag)
        while circuit.num_remain_nodes > 0:
            front_nodes = circuit.front_layer
            if len(front_nodes) == 0:
                raise ()
            for node in front_nodes:
                gates = self.get_node_gates(node)
                for gate in gates:
                    add_gate_to_qiskit_cir(cir_qiskit, gate)
            circuit.execute_front_layer()
        # add swaps

        for q0, q1 in swaps:
            cir_qiskit.swap(q0, q1)
        cir_qiskit.save_unitary()
        cir_qiskit = transpile(cir_qiskit, backend)
        job = backend.run(cir_qiskit)
        result = job.result()
        u = result.get_unitary(cir_qiskit)
        return u

    def check(self):
        """Check whether current DG is legal."""
        try:
            cycles = nx.find_cycle(self)
            print(cycles)
            raise ()
        except:
            pass
        # self.qiskit_circuit(save_to_file=False)

    def check_parallel(self, node1, node2):
        if (
            approx.local_node_connectivity(self, node1, node2) == 0
            and approx.local_node_connectivity(self, node2, node1) == 0
        ):
            return True
        else:
            return False

    def check_direct_dependency(self, node1, node2):
        """
        We say node2 directly depends on node1 if
            1) two nodes share at least one qubit;
            2) for each shared qubit, there can't be any nodes existing between
            the two nodes;
            3) there can't be any path connecting node1 and node2 other than the
                edge in 1)
        If two node are directly dependent, these nodes can be absorbed or
        cascaded. Note that currently we won't accept node1 and node2 are
        parallel, in that case, we will return False! One can use self.check_parallel
        to check the parallelism between nodes.
        """
        # check condition 1
        if (node1, node2) in self.edges:
            node_in, node_out = node1, node2
        else:
            if (node2, node1) in self.edges:
                node_in, node_out = node2, node1
            else:
                return False
        # check condition 3
        if approx.local_node_connectivity(self, node_in, node_out) > 1:
            return False
        return True

    def check_absorbable(self, node1, node2):
        """
        check if node1 and node2 can be obsorbed to each other
        node1 and node2 are absorbable if all qubits in node1 or node2 exist in
        node2 or node1 and they are directly dependent to each other.
        """
        if len(self.get_node_qubits(node1)) > len(self.get_node_qubits(node2)):
            node_abs, node_org = node2, node1
        else:
            node_abs, node_org = node1, node2
        for q in self.get_node_qubits(node_abs):
            if q not in self.get_node_qubits(node_org):
                return False
        if not self.check_direct_dependency(node_org, node_abs):
            return False
        return True

    def check_cascadeable(self, nodes1, node2, max_q_cascade):
        """
        Check if node2 can be cascaded with nodes in nodes1 (assuming nodes in
        nodes1 will be cascaded into 1 node)
        We accept node2 and nodes1 are parallel, i.e., there is no shared qubits
        between them.
        We assume all nodes in nodes1 can be cascaded and won't check this
        assumption!
        If the qubit number in the cascaded node is larger than max_q_cascade,
        we will always return False.
        """
        if len(nodes1) == 0:
            return True
        edge_qubits = []
        share_qubits = []
        qubits = self.get_node_qubits(node2).copy()
        # flag_1_2: node2 is the decendent of all nodes in nodes1
        # flag_2_1: node2 is the ancestor of all nodes in nodes1
        flag_1_2, flag_2_1 = False, False
        for node1 in nodes1:
            for q in self.get_node_qubits(node1):
                if q not in qubits:
                    qubits.append(q)
            share_qubits.extend(self.get_shared_qubits(node1, node2))
            if (node1, node2) in self.edges:
                flag_1_2 = True
                edge_qubits.extend(self.get_edge_qubits(((node1, node2))))
            if (node2, node1) in self.edges:
                flag_2_1 = True
                edge_qubits.extend(self.get_edge_qubits(((node2, node1))))
        if flag_1_2 and flag_2_1:
            raise ()
        if len(qubits) > max_q_cascade:
            return False
        if len(share_qubits) == 0:
            # if no shared qubits, we need to make sure they are parallel
            for node1 in nodes1:
                if not self.check_parallel(node1, node2):
                    return False
            return True

        # if node2 and any one in nodes1 can be cascaded, we return True
        for node1 in nodes1:
            if self.check_direct_dependency(node1, node2):
                return True
        return False

    #### Gate converter

    def schedule(self):
        """
        We will place each gate in each node in the right time slot.
        This placement will be stored in a 2-d list gate_placement in which
        gate_placement[i][j] = (node, k) represents the kth gate in node node
        will be placed in time slot (depth) i under qubit j.

        Besides, we will also generate a dict node_gate_to_depth in which each
        key is in the form of (node, k) and value [depths (sorted)].

        Note that 'depth' here starts from 0.

        Currently we don't support SWAPs implemented by CZs.
        """
        a = [None] * self.num_q
        gate_placement = []
        node_gate_to_depth = {}
        qubit_depth = [0] * self.num_q
        for node in nx.topological_sort(self):
            for k, (gate_name, qubits, _) in enumerate(
                self.get_node_gates(node)
            ):
                depth_ = []
                num_d = self.gate_depth[gate_name]
                d_start = max([qubit_depth[q] for q in qubits])
                depth_add = d_start + num_d - len(gate_placement)
                if depth_add > 0:
                    gate_placement.extend([a.copy() for i in range(depth_add)])
                for q in qubits:
                    qubit_depth[q] = d_start + num_d
                    for d in range(d_start, d_start + num_d):
                        # update gate_placement
                        gate_placement[d][q] = (node, k)
                        if d not in depth_:
                            # update depth_
                            depth_.append(d)
                node_gate_to_depth[(node, k)] = depth_
        return gate_placement, node_gate_to_depth
