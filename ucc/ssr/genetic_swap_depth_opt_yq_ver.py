# -*- coding: utf-8 -*-
"""
Created on Tue Jul  5 13:34:26 2022

@author: zhoux

The genetic algorithm for optimizing the depth of a quantum circuit output by
a SWAP-based QCT algorithm. It usilizes the commutation rules between a SWAP and
single- or CX gates.
"""

from copy import deepcopy
import numpy as np
import os

import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from ucc.ssr.circuittransform.inputs.cir_dg_swap_depth_opt import (
    DGSwap,
    hybridization4,
)

# parameters
num_species_default = 20
init_mutation_time_default = 5
mutation_rate_default = 0.8
max_iter_default = 50
max_idle_times_default = 15
flag_print = 0


def node_eq(node1, node2):
    if node1 == node2:
        return True
    else:
        return False


def equivalence_checking(dg1, dg2, ag):
    """
    Check the equivalence of two dgs that are only different in terms of the
    SWAP gates.
    """
    # check connectivity
    dg = dg1
    for node in dg.nodes:
        if node == dg.root:
            continue
        qubits = dg.get_node_qubits(node)
        if len(qubits) == 1:
            continue
        if len(qubits) == 2:
            if tuple(qubits) not in ag.edges:
                return False
        if len(qubits) > 2:
            print("dg1")
            print(qubits)
            raise ()
    dg = dg2
    for node in dg.nodes:
        if node == dg.root:
            continue
        qubits = dg.get_node_qubits(node)
        if len(qubits) == 1:
            continue
        if len(qubits) == 2:
            if tuple(qubits) not in ag.edges:
                return False
        if len(qubits) > 2:
            print("dg2")
            print(qubits)
            raise ()
    if len(ag) > 12:
        # print('We only check the connectivity due to the too large qubit number.')
        return True
    # check functionality
    num_q = dg1.num_q
    dg1, dg2 = deepcopy(dg1), deepcopy(dg2)
    dg1.remove_node(dg1.root), dg2.remove_node(dg2.root)
    u1 = dg1.get_unitary(num_q)
    u2 = dg2.get_unitary(num_q)
    error = np.sum(np.abs(u1 - u2))
    print("Error is", error)
    if error > 0.0001:
        return False
    else:
        return True


class SolutionsPool:
    def __init__(self, dg_ori):
        self.pool = []
        self.dg_ori = dg_ori
        self.cost_ori = self.dg_ori.cost
        self.solution_best = (np.inf, None)
        self.log_cost_min, self.log_cost_ave, self.log_cost_max = (
            None,
            None,
            None,
        )

    @property
    def best_dg(self):
        return self.solution_best[1]

    @property
    def best_cost(self):
        return self.solution_best[0]

    def get_ave_max_cost(self):
        cost_total = 0
        cost_max = -1 * np.inf
        for cost, _ in self.pool:
            cost_total += cost
            if cost > cost_max:
                cost_max = cost
        return cost_total / len(self.pool), cost_max

    def add_solution(self, dg, cost=None):
        if cost == None:
            cost = dg.cost
        self.pool.append((cost, dg))
        if cost < self.solution_best[0]:
            self.solution_best = (cost, deepcopy(dg))

    def init_log(self):
        self.log_cost_min, self.log_cost_ave, self.log_cost_max = [], [], []
        cost_ave, cost_max = self.get_ave_max_cost()
        self.log_cost_min.append(self.solution_best[0])
        self.log_cost_ave.append(cost_ave)
        self.log_cost_max.append(cost_max)

    def update_log(self):
        if self.log_cost_min == None:
            raise ()
        self.log_cost_min.append(self.solution_best[0])
        cost_ave, cost_max = self.get_ave_max_cost()
        self.log_cost_ave.append(cost_ave)
        self.log_cost_max.append(cost_max)
        if flag_print:
            print(
                "{}: {} {} {}, ".format(
                    str(len(self.log_cost_min)),
                    str(self.log_cost_min[-1]),
                    str(self.log_cost_ave[-1]),
                    str(self.log_cost_max[-1]),
                ),
                end="",
            )

    def worst_solution_index(self):
        if len(self.pool) < 1:
            raise ()
        cost_worst, index_worst = 0, None
        for i, solution in enumerate(self.pool):
            if solution[0] > cost_worst:
                cost_worst, index_worst = solution[0], i
        return index_worst

    def pick_solution_random(self, flag_copy, num=1):
        picked = []
        for _ in range(num):
            index = np.random.randint(len(self.pool))
            if flag_copy:
                picked.append(
                    (self.pool[index][0], deepcopy(self.pool[index][1]))
                )
            else:
                picked.append(self.pool[index])
        return picked

    def delete_worst_solution(self):
        if len(self.pool) <= 1:
            raise ()
        return self.pool.pop(self.worst_solution_index())

    def weed_out(self, survive_num):
        # if survive_num > len(self.pool): raise()
        while len(self.pool) > survive_num:
            self.delete_worst_solution()


def genetic_opt(index, qasm, ag, method_cost_func, basic_2_q_gate, path=None):
    """
    Genetic algorithm for opt. the circuit depth using SWAP based communation
    rules.
    """
    num_species = num_species_default
    init_mutation_time = init_mutation_time_default
    mutation_rate = mutation_rate_default
    max_iter = max_iter_default
    max_idle_times = max_idle_times_default
    # init cir_dg
    if isinstance(qasm, str):
        dg_ori = DGSwap(ag, basic_2_q_gate, method_cost_func)
        dg_ori.from_qasm(qasm, path=path)
        dg_ori.num_q = len(ag)
    else:
        dg_ori = qasm
    dg_baseline = deepcopy(dg_ori)
    evolution_count = 0
    # check depth
    from qiskit.converters import circuit_to_dag, dag_to_circuit

    from qiskit.transpiler.passes import Decompose
    from qiskit.circuit.library.standard_gates.swap import SwapGate

    cir_qiskit = dg_ori.qiskit_circuit()
    dag_qiskit = circuit_to_dag(cir_qiskit)
    de_pass = Decompose(gates_to_decompose=SwapGate)
    dag_qiskit = de_pass.run(dag_qiskit)
    cir_qiskit = dag_to_circuit(dag_qiskit)
    dg_ori.depth_to_node_list()
    # init species
    solutions_pool = SolutionsPool(dg_ori)
    for _ in range(num_species * 3):
        dg_new = deepcopy(dg_ori)
        evolution_count += dg_new.random_mutation(init_mutation_time)
        solutions_pool.add_solution(dg_new)
    solutions_pool.weed_out(num_species)
    solutions_pool.init_log()
    best_cost = solutions_pool.best_cost
    # # of times for continuous iterations that can't find any better solution
    count = 0
    # iteration
    for _ in range(max_iter):
        # generate new solutions
        count += 1
        for species_i in range(num_species):
            if species_i <= mutation_rate * num_species:
                # mutation
                solutions = solutions_pool.pick_solution_random(
                    flag_copy=True, num=1
                )  # original True
                cost, dg_new = solutions[0]
                evolution_count += dg_new.random_mutation2()
            else:
                # hybridization
                solutions = solutions_pool.pick_solution_random(
                    flag_copy=False, num=2
                )
                dg1, dg2 = solutions[0][1], solutions[1][1]
                dg_new = hybridization4(dg1, dg2, dg_ori)
                evolution_count += 1
            solutions_pool.add_solution(dg_new)
        # select best soultions
        solutions_pool.update_log()
        solutions_pool.weed_out(num_species)
        current_cost = solutions_pool.best_cost
        if current_cost < best_cost:
            best_cost, count = current_cost, 0
        if count > max_idle_times:
            break
    eq = equivalence_checking(dg_ori, solutions_pool.solution_best[1], ag)
    if not eq:
        raise ()

    return solutions_pool.best_dg
