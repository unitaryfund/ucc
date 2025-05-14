# -*- coding: utf-8 -*-
"""
Created on Sun May 23 23:44:08 2021

@author: Xiangzhen Zhou
"""
import numpy as np

def qubit_convert(q_list):
    pass

class FrontCircuit():
    def __init__(self, DG, AG, front_cir_from=None):
        '''
        

        Parameters
        ----------
        map_list : TYPE
            index: logical qubits
            value: physical qubits
        DG : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        self.DG = DG
        self.AG = AG
        self.num_q_phy = len(AG)
        self.num_q_log = DG.num_q
        self.__hash = None
        #self.unassigned_q = self.num_q_log
        if front_cir_from == None:
            self.num_remain_nodes = len(DG)
            # initial mapping
            self.log_to_phy = [-1] * self.num_q_log
            self.phy_to_log = [-1] * self.num_q_phy
            # find first gates and front layer
            # first gate value is -1 when the qubit has no gate in the front
            self.first_gates = [-1] * self.num_q_log
            self.front_layer = []
            current_nodes = []
            used_nodes = []
            for node in DG.nodes:
                if DG.in_degree[node] == 0:
                    current_nodes.append(node)
                    self.front_layer.append(node)
            i = 0
            while i < self.num_q_log and len(current_nodes) > 0:
                current_nodes.sort()
                node = current_nodes.pop(0)
                used_nodes.append(node)
                qubits = DG.nodes[node]['qubits']
                for q in qubits:
                    if self.first_gates[q] == -1:
                        self.first_gates[q] = node
                        i += 1
                for node_new in DG.successors(node):
                    if not node_new in used_nodes:
                        flag = True
                        for node_pre in DG.predecessors(node_new):
                            if not node_pre in used_nodes: flag = False
                        if flag == True: current_nodes.append(node_new)
            if i > self.num_q_log: raise()
        else:
            # copy
            self.num_remain_nodes = front_cir_from.num_remain_nodes
            # initial mapping
            self.log_to_phy = front_cir_from.log_to_phy.copy()
            self.phy_to_log = front_cir_from.phy_to_log.copy()
            # find first gates and front layer
            self.first_gates = front_cir_from.first_gates.copy()
            self.front_layer = front_cir_from.front_layer.copy()
            
    def __hash__(self):
        if self.__hash == None:
            info = tuple(self.front_layer), tuple(self.log_to_phy)
            self.__hash = hash(info)
        return self.__hash
    
    
    def _executable(self, node):
        '''judge whether a node is executable'''
        q_log0, q_log1 = self.DG.nodes[node]['qubits']
        q_phy0, q_phy1 = self.log_to_phy[q_log0], self.log_to_phy[q_log1]
        if q_phy0 != -1 and q_phy1 != -1:
            if (q_phy0, q_phy1) in self.AG.edges: return True
        return False
    
    def execute_front_layer(self):
        '''
        Execute all gates in the front layer regardless mapping
        However, we won't executable the following possible executable gates'
        '''
        layer = self.front_layer.copy()
        for node_dg in layer:
            self.execute_gate(node_dg)
        
    def execute_gates(self):
        '''find all executable gates and execute them'''
        exe_gates = []
        i = 0
        max_i = len(self.front_layer) - 1
        while i <= max_i:
            current_node = self.front_layer[i]
            # check cnot executable
            if self._executable(current_node):
                self.execute_gate_index(i)
                exe_gates.append(current_node)
                max_i = len(self.front_layer) - 1
            else:
                i += 1
        return exe_gates
    
    def execute_gate_index(self, front_layer_i):
        '''We only execute specified gate and will not execute its successors'''
        self.num_remain_nodes -= 1
        exe_node = self.front_layer.pop(front_layer_i)
        qubits = self.DG.nodes[exe_node]['qubits']
        nodes_next = list(self.DG.successors(exe_node))
        for q in qubits:
            if self.first_gates[q] != exe_node: 
                print("self.first_gates[q]", self.first_gates[q])
                print("exe_node", exe_node)
                raise()
        # deal with the successors of executed node
        ## here we assume the indices of nodes in DG follows the topological
        ## order
        for node in nodes_next:
            for q in self.DG.edges[(exe_node, node)]['qubits']:
                self.first_gates[q] = node
            flag = True
            for q in self.DG.nodes[node]['qubits']:
                if self.first_gates[q] != node:
                    flag = False
                    break
            if flag: self.front_layer.append(node)
                
    def execute_gate(self, node_DG):
        '''We only execute specified gate and will not execute its successors'''
        front_layer_i = self.front_layer.index(node_DG)
        self.execute_gate_index(front_layer_i)
            
        