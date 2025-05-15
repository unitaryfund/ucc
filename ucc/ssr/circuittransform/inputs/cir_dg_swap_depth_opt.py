# -*- coding: utf-8 -*-
"""
Created on Thu Jun 30 20:13:14 2022

@author: zhoux
This module provides a modified cir_dg (DGSwap) which can be used for optimizing
the depth of a circuit output by a QCT algorithm.

It accepts CNOT, SWAP and arbitrary single-qubit gate as nodes and the weight
of the incoming edge of a node represents the latency of the corresponding node.

The DGSwap has a root node connecting all nodes (gates) in the front layer.
"""

import networkx as nx
import numpy as np
from copy import deepcopy
from ucc.ssr.circuittransform.inputs.cir_dg import DG

# import sys
# sys.path.append("..")

from ucc.ssr.circuittransform.front_circuit import FrontCircuit


def swap_qubits_(qubits, swap_qubits):
    """Swap swap_qubits[0] and swap_qubits[1] in qubits list."""
    qubits_new = []
    for q in qubits:
        if q == swap_qubits[0]:
            qubits_new.append(swap_qubits[1])
        else:
            if q == swap_qubits[1]:
                qubits_new.append(swap_qubits[0])
            else:
                qubits_new.append(q)
    return qubits_new


def hybridization4(dg_swap1, dg_swap2, dg_ori):
    """
    For each exchange, we use dg_swap1 and then try to exchange using dg_swap2
    one-by-one and accept only that reducing depth.
    """
    dg_swap_new = deepcopy(dg_swap1)
    exchange2 = dg_swap2.exchange_log.copy()
    # depth_ori = dg_swap_new.depth
    depth_ori = dg_swap_new.fast_depth
    for node1, node2 in exchange2:
        if (node1, node2) in dg_swap_new.exchange_log or (
            node2,
            node1,
        ) in dg_swap_new.exchange_log:
            continue
        flag = dg_swap_new.exchange(node1, node2)
        if flag:
            # depth_new = dg_swap_new.depth
            depth_new = dg_swap_new.fast_depth
            if depth_new < depth_ori:
                # accept
                depth_ori = depth_new
            else:
                if depth_new == depth_ori:
                    # accept with 100% probability
                    if np.random.rand() < 1:
                        continue
                # recover
                dg_swap_new.exchange(node1, node2)
                dg_swap_new.exchange_log.pop(-1)
                dg_swap_new.exchange_log.pop(-1)

    return dg_swap_new


class DGSwap(DG):
    def __init__(self, ag, basic_2_q_gate, cost_func="depth"):
        super().__init__(basic_2_q_gate=basic_2_q_gate)
        # Should we disable positions before invoking a SAT solver?
        self.disable_pos_sat = 1
        # add root node
        # root node contains 0 gate and all qubits
        self.add_node(self.node_count)
        self.root = self.node_count
        self.node_count += 1
        self.nodes[self.root]["gates"] = []
        self.nodes[self.root]["qubits"] = list(range(len(ag)))
        self.qubit_to_node = [self.root] * len(ag)
        self.cost_func = cost_func
        # attrs
        self.swap_nodes = None
        self.ag = ag
        self.exchange_log = []
        self.node_to_depth = {}

    def clear_attrs(self):
        self.exchange_log = []
        self.swap_nodes = None

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]

        # 创建一个新对象但不调用 __init__
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        nx.DiGraph.__init__(result)
        result.add_nodes_from(
            (
                n,
                {
                    "gates": list(data["gates"]),
                    "qubits": list(data["qubits"]),
                    **(
                        {
                            "num_gate_1q": data["num_gate_1q"],
                            "num_gate_2q": data["num_gate_2q"],
                        }
                        if n != self.root
                        else {}
                    ),
                },
            )
            for n, data in self.nodes(data=True)
        )
        result.add_edges_from(
            (
                u,
                v,
                {
                    "qubits": list(data["qubits"]),
                    **(
                        {"depth": data["depth"]} if "depth" in data else {}
                    ),  # 只在原始数据中存在 'depth' 时才拷贝它
                },
            )
            for u, v, data in self.edges(data=True)
        )

        result.qubit_to_node = self.qubit_to_node[:]  # list 拷贝
        result.num_gate_2q = self.num_gate_2q
        result.num_gate_1q = self.num_gate_1q
        result.node_count = self.node_count
        result.num_q = self.num_q
        result.basic_2_q_gate = self.basic_2_q_gate
        result.gate_depth = self.gate_depth

        result.disable_pos_sat = self.disable_pos_sat
        result.root = self.root
        result.cost_func = self.cost_func
        result.swap_nodes = self.swap_nodes  # tuple, no effect
        result.ag = self.ag
        # result.exchange_log = deepcopy(self.exchange_log, memo)
        result.exchange_log = self.exchange_log[:]  # 安全、快速
        # result.node_to_depth = deepcopy(self.node_to_depth, memo)
        result.node_to_depth = {k: v[:] for k, v in self.node_to_depth.items()}
        # result.two_q_nodes = deepcopy(self.two_q_nodes, memo)

        return result

    @property
    def depth(self):
        """
        This method will repeatedly invoke shortest-length alg. in nx during
        each invoking, and hence is not efficient.
        """
        if self.basic_2_q_gate == "cx":
            return nx.dag_longest_path_length(self, weight="depth")
        else:
            raise ()

    @property
    def cost(self):
        if self.cost_func == "depth":
            return self.cost_depth

    @property
    def cost_depth(self):
        # return self.depth
        return self.fast_depth  # edit by yq

    # yq
    @property
    def fast_depth(self):
        return max(self.node_to_depth[max(self.node_to_depth)]) + 1

    # yq
    def set_disable(self, dis):
        self.disable_pos_sat = dis

    def add_to_exchange_log(self, exchange_nodes):
        self.exchange_log.append(exchange_nodes)

    # yq
    def add_swap_node(self):
        # swap_nodes, two_q_nodes = [], []
        swap_nodes = []
        for node in self.nodes:
            if node == self.root:
                continue
            if self.get_node_num_q(node) == 1:
                continue
            if len(self.get_node_gates(node)) > 1:
                raise ()
            name = self.get_node_gates(node)[0][0]
            if name == "swap":
                swap_nodes.append(node)
            elif name != self.basic_2_q_gate:
                raise (Exception(f"Unexpected gate type {name}."))

        self.swap_nodes = tuple(swap_nodes)

    def from_qasm(self, file, path=None):
        super().from_qasm(file, path=path, absorb=False)

        swap_nodes = []
        for node in self.nodes:
            if node == self.root:
                continue
            if self.get_node_num_q(node) == 1:
                continue
            if len(self.get_node_gates(node)) > 1:
                raise ()
            name = self.get_node_gates(node)[0][0]
            if name == "swap":
                swap_nodes.append(node)
            elif name != self.basic_2_q_gate:
                raise (Exception(f"Unexpected gate type {name}."))

        self.swap_nodes = tuple(swap_nodes)
        self.add_depth_to_all_edges()
        self.depth_to_node_list()  # add by yq

    def add_depth_to_all_edges(self):
        for edge in self.edges:
            self.add_depth_to_edge(edge)

    def add_depth_to_edge(self, edge):
        node = edge[1]
        gates = self.get_node_gates(node)
        if len(gates) != 1:
            raise ()
        self.edges[edge]["depth"] = self.gate_depth[gates[0][0]]

    def check_node_connectivity(self, node):
        qubits = self.get_node_qubits(node)
        if len(qubits) == 1:
            return True
        return qubits in self.ag.edges

    #### commutation rules
    def find_exchangable_edges(self, rules=("swap",)):
        """
        Find all edges gates in the end nodes of which can be exchanged via
        specific rules.

        Parameters
        ----------
        rules : TYPE, optional
            DESCRIPTION. The default is ("swap",).

        Returns
        -------
        exchangeable_edges : TYPE
            DESCRIPTION.

        """
        exchangeable_edges = []
        for edge in self.edges:
            if self.exchangeable(edge[0], edge[1], rules=rules):
                exchangeable_edges.append(edge)
        return exchangeable_edges

    def find_exchangable_edges_node(self, node, rules=("swap",)):
        """
        Find all edges (connected to the given node) the gates in the end nodes
        of which can be exchanged via specific rules.

        Parameters
        ----------
        rules : TYPE, optional
            DESCRIPTION. The default is ("swap_cx_cz",).

        Returns
        -------
        exchangeable_edges : TYPE
            DESCRIPTION.

        """
        exchangeable_edges = []
        for edge in self.edges(node):
            if self.exchangeable(edge[0], edge[1], rules=rules):
                exchangeable_edges.append(edge)
        return exchangeable_edges

    def exchangeable(
        self, node1, node2, rules=("swap",), impose_exchange=False
    ):
        """
        Check if node1 and node2 are exchangeable.
        Rules:
            swap:
                SWAP + any gate
        """
        if node1 == self.root or node2 == self.root:
            return False
        assert (
            self.get_node_num_gate(node1) <= 1
            and self.get_node_num_gate(node2) <= 1
        ), (
            f"Currently we only support the exchange rules in nodes with only 1 gate, but node {node1} and {node2} contain gates {self.get_node_gates(node1)} and {self.get_node_gates(node2)}"
        )

        if not self.check_direct_dependency(node1, node2):
            return False
        flag, rule_impose = self.__exchangeable(node1, node2, rules)
        if flag and impose_exchange:
            if rule_impose == "swap":
                flag = self.exchange_swap(
                    node1, node2, check_commutation=False
                )
            else:
                raise ()
        return flag

    def __exchangeable(self, node1, node2, rules):
        """
        Check if node1 and node2 are exchangeable.
        Rules:
            swap:
                SWAP + any gate
        """
        gate1, gate2 = (
            self.get_node_gates(node1)[0],
            self.get_node_gates(node2)[0],
        )
        qubits1, qubits2 = gate1[1], gate2[1]
        if "swap" in rules:
            if gate1[0] == "swap" or gate2[0] == "swap":
                ## check qubits connectivity after exchanging
                if gate1[0] == "swap":
                    swap_node, non_swap_node = node1, node2
                    swap_qubits = qubits1
                else:
                    swap_node, non_swap_node = node2, node1
                    swap_qubits = qubits2
                ## get shared qubits
                qubits = self.get_node_qubits(non_swap_node)
                qubits_swap = swap_qubits_(qubits, swap_qubits)
                if len(qubits_swap) == 1 or (
                    len(qubits_swap) == 2 and qubits_swap in self.ag.edges
                ):
                    return True, "swap"
        return False, None

    def random_mutation(self, mutate_time, max_try=None):
        """
        Randomly choose mutate_time SWAP node pairs to do exchanging
        Return:
            The number of exchanges having been done.
        """
        if max_try == None:
            max_try = mutate_time * 2
        count = 0
        for _ in range(max_try):
            if count >= mutate_time:
                break
            swap_node = np.random.choice(self.swap_nodes)
            candidate_nodes = list(self.predecessors(swap_node))
            candidate_nodes.extend(list(self.successors(swap_node)))
            # try to pick up the second node to be exchanged
            for _ in range(5):
                non_swap_node = np.random.choice(candidate_nodes)
                if self.exchange_swap(swap_node, non_swap_node):
                    count += 1
                    break
        return count

    def random_mutation2(self, max_try=None):
        """
        Randomly choose max_try SWAP node pairs to do exchanging until depth
        is changed.
        Return:
            The number of exchanges having been done.
        """
        # depth_ori = self.depth
        depth_ori = self.fast_depth
        if max_try == None:
            max_try = 50
        count = 0
        for _ in range(max_try):
            swap_node = np.random.choice(self.swap_nodes)
            candidate_nodes = list(self.predecessors(swap_node))
            candidate_nodes.extend(list(self.successors(swap_node)))
            # try to pick up the second node to be exchanged
            for _ in range(5):
                non_swap_node = np.random.choice(candidate_nodes)
                if self.exchange_swap(swap_node, non_swap_node):
                    count += 1
                    break
            # depth_c = self.depth
            depth_c = self.fast_depth

            if depth_c != depth_ori:
                break

        return count

    def exchange_swap(self, node1, node2, check_commutation=True):
        """
        Exchange the positions of node1 and node2. At least one node must contain
        SWAP gate.
        """
        # check commutation
        if check_commutation:
            if not self.exchangeable(node1, node2, rules=("swap",)):
                return False
        gate1, gate2 = (
            self.get_node_gates(node1)[0],
            self.get_node_gates(node2)[0],
        )
        # get swap and none swap gate
        if gate1[0] == "swap":
            swap_node, non_swap_node = node1, node2
        elif gate2[0] == "swap":
            swap_node, non_swap_node = node2, node1
        else:
            raise (
                Exception(
                    f"There is no SWAP in nodes {node1} and {node2} but exchange_swap method is imposed."
                )
            )
        edge1, edge2 = (node1, node2), (node2, node1)
        edge = None
        if edge1 in self.edges:
            edge = edge1
        if edge2 in self.edges:
            edge = edge2
        if edge == None:
            raise ()
        # exchange nodes
        swap_qubits = self.get_node_qubits(swap_node)
        ## get shared qubits
        shared_qubits_non_swap = self.get_edge_qubits(edge)
        shared_qubits_swap = swap_qubits_(shared_qubits_non_swap, swap_qubits)
        ## check qubits connectivity after exchanging
        qubits = self.get_node_qubits(non_swap_node)
        qubits_swap = swap_qubits_(qubits, swap_qubits)
        if len(qubits_swap) == 2:
            if qubits_swap not in self.ag.edges:
                return False
        ## get predecessors and successors

        affected_nodes = set(nx.descendants(self, node1)) | set(
            nx.descendants(self, node2)
        )

        pre_nodes, succ_nodes = [], []
        for node_pre in list(self.predecessors(edge[0])):
            if edge[0] == swap_node:
                shared_qubits = shared_qubits_swap
            else:
                shared_qubits = shared_qubits_non_swap
            qubits_new = []
            ## delete shared qubits in edges
            for q_pre in self.get_edge_qubits((node_pre, edge[0])):
                if q_pre not in shared_qubits:
                    qubits_new.append(q_pre)
            if len(qubits_new) == 0:
                self.remove_edge(node_pre, edge[0])
                pre_nodes.append(node_pre)
            else:
                if len(qubits_new) < len(
                    self.get_edge_qubits((node_pre, edge[0]))
                ):
                    self.set_edge_qubits((node_pre, edge[0]), qubits_new)
                    pre_nodes.append(node_pre)
        for node_succ in list(self.successors(edge[1])):
            if edge[1] == swap_node:
                shared_qubits = shared_qubits_swap
            else:
                shared_qubits = shared_qubits_non_swap
            qubits_new = []
            ## delete shared qubits in edges
            for q_succ in self.get_edge_qubits((edge[1], node_succ)):
                if q_succ not in shared_qubits:
                    qubits_new.append(q_succ)
            if len(qubits_new) == 0:
                self.remove_edge(edge[1], node_succ)
                succ_nodes.append(node_succ)
            else:
                if len(qubits_new) < len(
                    self.get_edge_qubits((edge[1], node_succ))
                ):
                    self.set_edge_qubits((edge[1], node_succ), qubits_new)
                    succ_nodes.append(node_succ)
        ## swap based exchange
        self.remove_edge(edge[0], edge[1])
        ### update qubits in non-swap node
        self.nodes[non_swap_node]["qubits"] = qubits_swap
        gate = self.get_node_gates(non_swap_node)[0]
        gate_new = gate[0], tuple(swap_qubits_(gate[1], swap_qubits)), gate[2]
        self.nodes[non_swap_node]["gates"] = [gate_new]
        ### add back edge
        self.add_line(edge[1], edge[0])
        self.add_depth_to_edge((edge[1], edge[0]))
        ### add new edges
        for node_pre in pre_nodes:
            self.add_line(node_pre, edge[1])
            self.add_depth_to_edge((node_pre, edge[1]))
        for node_succ in succ_nodes:
            self.add_line(edge[0], node_succ)
            self.add_depth_to_edge((edge[0], node_succ))
        self.exchange_log.append((node1, node2))
        self.swap_update(affected_nodes, node1, node2)
        return True

    # yq
    def swap_update(self, affected_nodes, node1, node2):
        affected_nodes = list(affected_nodes)

        affected_nodes.sort(key=lambda n: max(self.node_to_depth.get(n, [0])))
        if (node1, node2) in self.edges:
            affected_nodes.insert(0, node2)
            affected_nodes.insert(0, node1)
        else:
            affected_nodes.insert(0, node1)
            affected_nodes.insert(0, node2)

        for node in affected_nodes:
            predecessors = list(self.predecessors(node))
            old_depth = max(self.node_to_depth[node])
            # print("affect node", node)
            if predecessors:
                # print(self.node_to_depth[node])
                depth_minus = [
                    d - self.node_to_depth[node][0] + 1
                    for d in self.node_to_depth[node]
                ]
                # print("depth_minus", depth_minus)
                max_depth = -1
                for p in predecessors:
                    if p == self.root:
                        continue
                    max_p_depth = max(self.node_to_depth[p])
                    if max_p_depth > max_depth:
                        max_depth = max_p_depth

                # print("max_depth", max_depth)

                new_depth = [max_depth + dm for dm in depth_minus]
                # print("new_depth", new_depth)
                self.node_to_depth[node] = new_depth
                max_new_depth = max(new_depth)

            else:
                self.node_to_depth[node] = [0]

    def exchange_nodes(self, node1, node2):
        """
        Exchange the positions of node1 and node2. None of nodes contain
        SWAP gate.
        We won't check communtation.
        """
        if node1 == self.root or node2 == self.root:
            return False
        gate1, gate2 = (
            self.get_node_gates(node1)[0],
            self.get_node_gates(node2)[0],
        )
        # check
        if gate1[0] == "swap" or gate2[0] == "swap":
            raise ()
        if not self.check_direct_dependency(node1, node2):
            raise ()

        edge1, edge2 = (node1, node2), (node2, node1)
        edge = None
        if edge1 in self.edges:
            edge = edge1
        if edge2 in self.edges:
            edge = edge2
        if edge == None:
            raise ()
        # exchange nodes
        ## get shared qubits
        shared_qubits = self.get_shared_qubits(node1, node2)
        ## get predecessors and successors
        pre_nodes, succ_nodes = [], []
        for node_pre in list(self.predecessors(edge[0])):
            qubits_new = []
            ## delete shared qubits in edges
            for q_pre in self.get_edge_qubits((node_pre, edge[0])):
                if q_pre not in shared_qubits:
                    qubits_new.append(q_pre)
            if len(qubits_new) == 0:
                self.remove_edge(node_pre, edge[0])
                pre_nodes.append(node_pre)
            else:
                if len(qubits_new) < len(
                    self.get_edge_qubits((node_pre, edge[0]))
                ):
                    self.set_edge_qubits((node_pre, edge[0]), qubits_new)
                    pre_nodes.append(node_pre)
        for node_succ in list(self.successors(edge[1])):
            qubits_new = []
            ## delete shared qubits in edges
            for q_succ in self.get_edge_qubits((edge[1], node_succ)):
                if q_succ not in shared_qubits:
                    qubits_new.append(q_succ)
            if len(qubits_new) == 0:
                self.remove_edge(edge[1], node_succ)
                succ_nodes.append(node_succ)
            else:
                if len(qubits_new) < len(
                    self.get_edge_qubits((edge[1], node_succ))
                ):
                    self.set_edge_qubits((edge[1], node_succ), qubits_new)
                    succ_nodes.append(node_succ)
        ## swap based exchange
        self.remove_edge(edge[0], edge[1])
        ### add back edge
        self.add_line(edge[1], edge[0])
        self.add_depth_to_edge((edge[1], edge[0]))
        ### add new edges
        for node_pre in pre_nodes:
            self.add_line(node_pre, edge[1])
            self.add_depth_to_edge((node_pre, edge[1]))
        for node_succ in succ_nodes:
            self.add_line(edge[0], node_succ)
            self.add_depth_to_edge((edge[0], node_succ))
        self.exchange_log.append((node1, node2))
        return True

    def exchange(self, node1, node2):
        """Try two exchange any two nodes"""
        if not self.exchangeable(node1, node2):
            return False
        gate1, gate2 = (
            self.get_node_gates(node1)[0],
            self.get_node_gates(node2)[0],
        )
        # check commutation
        if gate1[0] == "swap" or gate2[0] == "swap":
            if np.random.rand() < 0.5:
                return self.exchange_swap(node1, node2)
            else:
                return self.exchange_swap(node2, node1)
        else:
            return self.exchange_nodes(node1, node2)

    def get_nodes_group(self):
        nodes_group = []
        for node in self.nodes:
            if node == self.root:
                continue
            if self.nodes[node]["num_gate_2q"] > 1:
                nodes_group.append(node)

        return nodes_group

    # yq: combine 2q gates simple version
    def combine_2q_gates_simple(self, max_q=5, combine_level=np.inf):
        nodes_groups = {}
        dg_new = deepcopy(self)
        dg_new.clear_attrs()
        edges = self.ag.edges
        cascade_count = 1
        it_count = 0
        while cascade_count > 0 and it_count < combine_level:
            cascade_count = 0
            it_count += 1
            qubit_to_node = [-1] * self.num_q  # current qubits associated node
            for node_ori in list(nx.topological_sort(dg_new)):
                if node_ori == dg_new.root:
                    continue
                if dg_new.get_node_num_q(node_ori) == 1:
                    continue
                if dg_new.get_node_num_q(node_ori) > 2:
                    # raise()
                    pass
                # 2 qubits
                node_new = node_ori
                if node_new not in nodes_groups:
                    nodes_groups[node_new] = [node_ori]
                for (
                    node_pre_new
                ) in qubit_to_node:  # to check last node in the qubit
                    if node_pre_new not in dg_new:
                        continue
                    flag_cascade = False
                    if dg_new.check_direct_dependency(
                        node_pre_new, node_new
                    ):  # current qubits' last node, a
                        # check qubit number
                        qubits = dg_new.get_node_qubits(node_pre_new).copy()
                        for q in dg_new.get_node_qubits(node_new):
                            if q not in qubits:
                                qubits.append(q)
                        if len(qubits) <= max_q:
                            flag_cascade = True  # can combine
                        # if these two nodes are parallel and share at least one
                        # edge in AG, we still cascade them
                    if not flag_cascade:
                        if dg_new.check_cascadeable(
                            [node_pre_new], node_new, max_q_cascade=max_q
                        ):
                            for q1 in dg_new.get_node_qubits(node_pre_new):
                                for q2 in dg_new.get_node_qubits(node_new):
                                    if q1 == q2:
                                        raise ()
                                    if (q1, q2) in edges:
                                        flag_cascade = True
                                    if flag_cascade:
                                        break
                                if flag_cascade:
                                    break
                    if flag_cascade:  # if ok for combine
                        cascade_count += 1
                        new_group = nodes_groups.pop(node_new)
                        new_group.extend(nodes_groups.pop(node_pre_new))
                        node_new = dg_new.cascade_node(node_pre_new, node_new)
                        nodes_groups[node_new] = new_group

                for q in dg_new.get_node_qubits(node_new):
                    qubit_to_node[q] = node_new
        return dg_new

    def break_all_nodes(self, decompose_swap):
        """Make each node contains only one gate and return a new dg."""
        dg_new = DGSwap(
            ag=self.ag,
            basic_2_q_gate=self.basic_2_q_gate,
            cost_func=self.cost_func,
        )
        dg_new.clear_attrs()
        dg_new.from_qiskit_circuit(
            self.qiskit_circuit(decompose_swap=decompose_swap), absorb=False
        )
        return dg_new

    def cx_to_swap(self):
        """Try to combine all 3 consecutive CNOTs to 1 SWAP"""
        self.clear_attrs()
        all_swap_nodes = []
        for node in list(self.nodes):
            if node == self.root:
                continue
            if node not in self.nodes:
                continue
            swap_nodes = []
            qubits = self.get_node_qubits(node)
            if len(qubits) != 2:
                continue
            q0, q1 = qubits
            for _ in range(3):
                gates = self.get_node_gates(node)
                if len(gates) != 1:
                    raise ()
                if gates[0][0] != "cx":
                    break
                q00, q11 = self.get_node_qubits(node)
                if q00 != q0 or q11 != q1:
                    if q00 != q1 or q11 != q0:
                        break
                swap_nodes.append(node)
                if self.out_degree[node] != 1:
                    break
                node = list(self.successors(node))[0]
            if len(swap_nodes) == 3:
                node = self.cascade_node(swap_nodes[0], swap_nodes[1])
                node = self.cascade_node(node, swap_nodes[2])
                self.nodes[node]["gates"] = [("swap", (q0, q1), [])]
                self.nodes[node]["qubits"] = [q0, q1]
                (
                    self.nodes[node]["num_gate_1q"],
                    self.nodes[node]["num_gate_2q"],
                ) = 0, 1
                all_swap_nodes.append(node)
        self.swap_nodes = tuple(all_swap_nodes)

    def decompose_swaps(self):
        """Decompose all SWAPs"""
        if self.basic_2_q_gate == "cx":
            self.swap_to_cx()

    def swap_to_cx(self):
        """
        Decompose each SWAP gate in a node into 3 CNOTs.
        """
        self.clear_attrs()
        for node in self.nodes:
            if node == self.root:
                continue
            qubits = self.get_node_qubits(node)
            if len(qubits) < 2:
                continue
            gates = self.get_node_gates(node)
            gates_new = []
            for gate in gates:
                if gate[0] == "swap" or gate[0] == "SWAP":
                    q0, q1 = gate[1]
                    gates_new.append(("cx", (q0, q1), []))
                    gates_new.append(("cx", (q1, q0), []))
                    gates_new.append(("cx", (q0, q1), []))
                    self.nodes[node]["num_gate_2q"] += 2
                    self.num_gate_2q += 2
                else:
                    gates_new.append(gate)
            self.nodes[node]["gates"] = gates_new

    def get_node_cx_list(self, node):
        """If there existing SWAP, we decompose it into 3 CNOTs"""
        cx_list = []
        names = ("cx", "swap")
        for name, qubits, _ in self.get_node_gates(node):
            if name not in names:
                raise ()
            if name == "cx":
                cx_list.append(tuple(qubits))
            if name == "swap":
                cx_list.extend(
                    [
                        (qubits[0], qubits[1]),
                        (qubits[1], qubits[0]),
                        (qubits[0], qubits[1]),
                    ]
                )
        return cx_list

    # yq
    def find_depth_disables_yq_ver(self, node):
        # print("find dis node", node)
        # print(self.nodes[node])
        gate_placement, node_gate_to_depth = self.schedule()
        node_qubits, node_gates = (
            self.get_node_qubits(node),
            self.get_node_gates(node),
        )
        # find the first and last time slot for each qubit
        qubits_time_slot_min = {q: np.inf for q in node_qubits}
        qubits_time_slot_max = {q: -1 * np.inf for q in node_qubits}
        min_qubits_to_gate = {q: np.inf for q in node_qubits}
        max_qubits_to_gate = {q: np.inf for q in node_qubits}
        for k, (gate_name, gate_qubits, _) in enumerate(node_gates):
            depths = node_gate_to_depth[(node, k)]
            d_min, d_max = min(depths), max(depths)
            for q in gate_qubits:
                if d_min < qubits_time_slot_min[q]:
                    qubits_time_slot_min[q] = d_min
                    min_qubits_to_gate[q] = (node, k)
                if d_max > qubits_time_slot_max[q]:
                    qubits_time_slot_max[q] = d_max
                    max_qubits_to_gate[q] = (node, k)
        # process left Nodes
        qubits_unchecked = deepcopy(node_qubits)
        while qubits_unchecked:
            process_qubit = qubits_unchecked[0]
            process_node = min_qubits_to_gate[process_qubit]
            min_depths_right = max(node_gate_to_depth[process_node])
            [min_q0, min_q1] = [
                qubit
                for qubit in node_qubits
                if gate_placement[min_depths_right][qubit] == process_node
            ]
            depth_beg = min_depths_right + 1
            while depth_beg < max(qubits_time_slot_max.values()):
                if (
                    gate_placement[depth_beg][min_q0] == None
                    and gate_placement[depth_beg][min_q1] == None
                ):
                    qubits_time_slot_min[min_q0] = (
                        depth_beg - len(node_gate_to_depth[process_node]) + 1
                    )
                    qubits_time_slot_min[min_q1] = (
                        depth_beg - len(node_gate_to_depth[process_node]) + 1
                    )
                    depth_beg += 1
                else:
                    break
            if min_q0 in qubits_unchecked:
                qubits_unchecked.remove(min_q0)
            if min_q1 in qubits_unchecked:
                qubits_unchecked.remove(min_q1)

        # process right Nodes
        qubits_unchecked = deepcopy(node_qubits)
        while qubits_unchecked:
            process_qubit = qubits_unchecked[0]
            process_node = max_qubits_to_gate[process_qubit]
            max_depths_left = min(node_gate_to_depth[process_node])
            [max_q0, max_q1] = [
                qubit
                for qubit in node_qubits
                if gate_placement[max_depths_left][qubit] == process_node
            ]
            depth_beg = max_depths_left - 1
            while depth_beg > min(qubits_time_slot_min.values()):
                if (
                    gate_placement[depth_beg][max_q0] == None
                    and gate_placement[depth_beg][max_q1] == None
                ):
                    qubits_time_slot_max[max_q0] = (
                        depth_beg + len(node_gate_to_depth[process_node]) - 1
                    )
                    qubits_time_slot_max[max_q1] = (
                        depth_beg + len(node_gate_to_depth[process_node]) - 1
                    )
                    depth_beg -= 1
                else:
                    break

            if max_q0 in qubits_unchecked:
                qubits_unchecked.remove(max_q0)
            if max_q1 in qubits_unchecked:
                qubits_unchecked.remove(max_q1)

        time_slot_start = min(qubits_time_slot_min.values())
        time_slot_end = max(qubits_time_slot_max.values())
        time_slot_total = time_slot_end - time_slot_start + 1

        # find disabled positions
        disabled_positions_reduced, disabled_positions_ori = [], []
        disabled_left_reduced, disabled_right_reduced = [], []
        for q in node_qubits:
            # disable left positions
            last_used_pos = 0
            for d_reduce in range(time_slot_total):
                d_ori = time_slot_start + d_reduce
                if d_ori < qubits_time_slot_min[q]:
                    if (
                        gate_placement[d_ori][q] != None
                        and gate_placement[d_ori][q][0] != node
                    ):
                        disabled_positions_reduced.append((last_used_pos, q))
                        disabled_positions_ori.append(
                            (time_slot_start + last_used_pos, q)
                        )
                        disabled_left_reduced.append((last_used_pos, q))
                        last_used_pos += 1
                else:
                    break
            # disable right positions
            last_used_pos = time_slot_total - 1
            for d_reduce in range(time_slot_total - 1, -1, -1):
                d_ori = time_slot_start + d_reduce
                if d_ori > qubits_time_slot_max[q]:
                    if (
                        gate_placement[d_ori][q] != None
                        and gate_placement[d_ori][q][0] != node
                    ):
                        disabled_positions_reduced.append((last_used_pos, q))
                        disabled_positions_ori.append(
                            (time_slot_start + last_used_pos, q)
                        )
                        disabled_right_reduced.append((last_used_pos, q))
                        last_used_pos -= 1
                else:
                    break
        return (
            time_slot_total,
            (disabled_positions_reduced, disabled_positions_ori),
            (disabled_left_reduced, disabled_right_reduced),
        )

    def recompile_cx_node_appro(
        self, node, predict_depth=None, print_info=False
    ):
        from ucc.ssr.circuittransform.recompile.recompile_sat import (
            recompile_cx_yq,
            recompile_cx_yq_predict,
        )

        cx_list = self.get_node_cx_list(node)
        depth_ori = self.get_node_depth(node)
        if depth_ori == 1:
            return False, 0, 0, 0
        depth_max, (disabled_positions, _), (dis_left, dis_right) = (
            self.find_depth_disables_yq_ver(node)
        )
        if predict_depth != None:
            (
                cx_list_re,
                cx_list_depth_re,
                flag,
                Sat_times,
                variable_cout,
                cnf_total,
            ) = recompile_cx_yq_predict(
                cx_list,
                self.ag,
                max_depth=depth_max,
                predict_depth=predict_depth,
                disabled_pos=disabled_positions,
                dis_left=dis_left,
                dis_right=dis_right,
                max_time=300,
                print_info=0,
                min_num_q_compile=16,
            )
        else:
            (
                cx_list_re,
                cx_list_depth_re,
                flag,
                Sat_times,
                variable_cout,
                cnf_total,
            ) = recompile_cx_yq(
                cx_list,
                self.ag,
                max_depth=depth_max,
                disabled_pos=disabled_positions,
                dis_left=dis_left,
                dis_right=dis_right,
                max_time=300,
                print_info=0,
                min_num_q_compile=16,
            )
        gates_new = []
        if len(cx_list_re) > 0:
            for qubits in cx_list_re:
                gates_new.append(("cx", tuple(qubits), []))
            # get original depth
            cir_qiskit = self.qiskit_circuit(decompose_swap=True)
            cir_qiskit_depth = cir_qiskit.depth()
            gates_ori = self.nodes[node]["gates"]
            self.nodes[node]["gates"] = gates_new
            # modified by yq
            or_num_gate_2q = self.nodes[node]["num_gate_2q"]
            self.nodes[node]["num_gate_2q"] = len(gates_new)
            #####
            # get opt. depth
            cir_qiskit2 = self.qiskit_circuit(decompose_swap=True)
            cir_qiskit2_depth = cir_qiskit2.depth()
            if cir_qiskit_depth <= cir_qiskit2_depth:
                self.nodes[node]["gates"] = gates_ori
                # modified by yq
                self.nodes[node]["num_gate_2q"] = or_num_gate_2q
                #####
                cir_qiskit_depth = cir_qiskit.depth()
                cir_qiskit2_depth = cir_qiskit2.depth()
                flag = False
            else:
                # if the compiled circuit reduces the total depth, we accept
                # this result
                flag = True
                if print_info:
                    print("deptn after", self.get_node_depth(node))
                    print(cx_list_re)
        else:
            flag = False
        return flag, Sat_times, variable_cout, cnf_total

    def qiskit_circuit(
        self,
        save_to_file=False,
        add_barrier=False,
        decompose_swap=False,
        file_name="circuit",
    ):
        dg = self
        return super(DGSwap, dg).qiskit_circuit(
            save_to_file=save_to_file,
            add_barrier=add_barrier,
            decompose_swap=decompose_swap,
            file_name=file_name,
        )

    def depth_to_node_list(self):
        """

        node_to_depth list

        Notice that in this method each node can contain more than one gate.
        Also note that depth here starts from 0.

        """
        depth = self.qiskit_circuit(decompose_swap=True).depth()
        num_q = len(self.ag)
        # depth_to_node = [[None]*num_q for _ in range(depth)]
        self.node_to_depth = {node: [] for node in self.nodes}

        # init circuits
        qubit_to_depth = [-1] * num_q
        circuit = FrontCircuit(self, self.ag)
        # add gates one by one
        while circuit.num_remain_nodes > 0:
            front_nodes = circuit.front_layer
            if self.root in front_nodes:
                circuit.execute_front_layer()
            if len(front_nodes) == 0:
                raise ()
            for node in front_nodes:
                for name, qubits, _ in self.get_node_gates(node):
                    depth_add = self.gate_depth[name]
                    current_depth = max([qubit_to_depth[q] for q in qubits])
                    # update depth_to_node and node_to_depth
                    for _ in range(depth_add):
                        current_depth += 1
                        if current_depth not in self.node_to_depth[node]:
                            self.node_to_depth[node].append(current_depth)
                    # update qubit_to_depth
                    for q in qubits:
                        qubit_to_depth[q] = current_depth

            circuit.execute_front_layer()
