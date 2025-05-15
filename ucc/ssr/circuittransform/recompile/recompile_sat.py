# -*- coding: utf-8 -*-
"""
Created on Wed Jul 27 23:26:19 2022

@author: zhoux

https://pysathq.github.io/docs/html/index.html
"""

import numpy as np
import networkx as nx
from pysat.formula import CNF
from pysat.solvers import Solver
from pysat.card import CardEnc, EncType

# from pysat.pb import *
# from pysat.card import *
from copy import deepcopy
import time


def interrupt(s):
    s.interrupt()


def not_(cnf_list):
    """
    Encode NOT(cnf_list)
    """
    raise ()


def and_equal(x, y, z):
    """
    Encode z == AND(x, y) to a CNF list
    """
    if x <= 0 or y <= 0 or z <= 0:
        raise ()
    if x == y or x == z or y == z:
        raise ()
    return [
        [-1 * z, x, y],
        [-1 * z, x, -1 * y],
        [-1 * z, -1 * x, y],
        [z, -1 * x, -1 * y],
    ]


def xor_equal(x, y, z):
    """
    Encode z == XOR(x, y) to a CNF list
    Page 102, "EQUIVALENCE CHECKING OF DIGITAL CIRCUITS"
    """
    if x <= 0 or y <= 0 or z <= 0:
        raise ()
    if x == y or x == z or y == z:
        raise ()
    return [
        [-1 * z, x, y],
        [-1 * z, -1 * x, -1 * y],
        [z, -1 * x, y],
        [z, x, -1 * y],
    ]


def if_c_then(c, cnf_list):
    """Encode if c, then cnf_list to a CNF list"""
    if c <= 0:
        raise ()
    for cnf_clause in cnf_list:
        cnf_clause.append(-1 * c)
    return cnf_list


def if_x_then_liters(x, liters):
    """Encode if x, then all literals must be satisfied"""
    cnf_list = []
    for l in liters:
        cnf_list.append([-1 * x, l])
    return cnf_list


def if_liters_then_x(liters, x):
    """Encode if all literals are satisfied, then x=1"""
    cnf = [x]
    for l in liters:
        cnf.append(-1 * l)
    return [cnf]


def if_c_then_xor_equal(c, x, y, z):
    """Encode if c, then z == XOR(x, y) to a CNF list"""
    cnf_list = xor_equal(x, y, z)
    return if_c_then(c, cnf_list)


def if_x_neq_y_then(x, y, cnf_list):
    """Encode if x != y, then cnf_list to a CNF list"""
    num = len(cnf_list)
    for i in range(num):
        cnf_clause = cnf_list[i]
        cnf_clause2 = cnf_clause.copy()
        cnf_clause.extend([-1 * x, y])
        cnf_clause2.extend([x, -1 * y])
        cnf_list.append(cnf_clause2)
    return cnf_list


START_DEPTH_RATIO = 0.5


def get_general_cnf(
    matrix_initial,
    target_depth,
    ag_graph,
    variable_count,
    qubits_ori_to_reduce,
    qubits_reduce_to_ori,
):
    # print("qubits reduced to ori ",qubits_reduce_to_ori )
    qubits = list(ag_graph.nodes())
    num_q = len(qubits)
    edges = [
        (qubits_ori_to_reduce[u], qubits_ori_to_reduce[v])
        for (u, v) in ag_graph.edges()
    ]
    m = np.empty((target_depth + 1, num_q, num_q), dtype="int")
    for i in range(m.size):
        variable_count += 1
        m.flat[i] = variable_count

    g = []
    for d in range(target_depth):
        g.append({})
        for q0, q1 in edges:
            variable_count += 1
            g[d][(q0, q1)] = int(variable_count)
            variable_count += 1
            g[d][(q1, q0)] = int(variable_count)

    id_row, id_col = [], []
    for d in range(target_depth + 1):
        id_row.append([])
        id_col.append([])
        for q in range(num_q):
            variable_count += 1
            id_row[d].append(int(variable_count))
            variable_count += 1
            id_col[d].append(int(variable_count))
    # init constraint C1
    cnf = CNF()
    for d in range(target_depth):
        cnf_add = []
        for q0, q1 in edges:
            cnf_add.extend([g[d][(q0, q1)], g[d][(q1, q0)]])
        cnf.append(cnf_add)
    # set revised constraint C2
    for d in range(target_depth):
        for c in range(num_q):
            variables_ = []
            for t in ag_graph.adj[qubits_reduce_to_ori[c]]:
                t = qubits_ori_to_reduce[t]
                variables_.extend([g[d][(c, t)], g[d][(t, c)]])
            cnf.extend(
                CardEnc.atmost(
                    lits=variables_, bound=1, encoding=EncType.pairwise
                )
            )
    # set constraint C3
    for d in range(target_depth):
        for c in range(num_q):
            for t in ag_graph.adj[qubits_reduce_to_ori[c]]:
                t = qubits_ori_to_reduce[t]
                cnf_add = []
                for j in range(num_q):
                    cnf_add.extend(
                        xor_equal(m[d][t][j], m[d][c][j], m[d + 1][t][j])
                    )
                if_c_then(g[d][(c, t)], cnf_add)
                cnf.extend(cnf_add)
    # set constraint C4
    for d in range(target_depth):
        for t in range(num_q):
            for j in range(num_q):
                variables_ = []
                for c in ag_graph.adj[qubits_reduce_to_ori[t]]:
                    c = qubits_ori_to_reduce[c]
                    variables_.append(g[d][(c, t)])
                cnf_add = CardEnc.equals(
                    lits=variables_, bound=1, encoding=EncType.pairwise
                ).clauses
                if_x_neq_y_then(m[d + 1][t][j], m[d][t][j], cnf_add)
                cnf.extend(cnf_add)

    # make m variables in depth 0 equal initial matrix
    for i in range(num_q):
        for j in range(num_q):
            cnf_add = CardEnc.equals(
                lits=[int(m[0][i][j])],
                bound=int(matrix_initial[i][j]),
                encoding=EncType.pairwise,
            )
            cnf.extend(cnf_add)

    for d in range(target_depth + 1):
        for q in range(num_q):
            raw_vs, col_vs = [], []
            for i, v in enumerate(m[d][q][:]):
                v = int(v)
                if i != q:
                    raw_vs.append(-1 * v)
                    cnf.append([-1 * v, -1 * id_row[d][q]])
                else:
                    raw_vs.append(v)
                    cnf.append([v, -1 * id_row[d][q]])
            cnf.extend(if_liters_then_x(raw_vs, id_row[d][q]))
            for i, v in enumerate(m[d, :, q]):
                v = int(v)
                if i != q:
                    col_vs.append(-1 * v)
                    cnf.append([-1 * v, -1 * id_col[d][q]])
                else:
                    col_vs.append(v)
                    cnf.append([v, -1 * id_col[d][q]])
            cnf.extend(if_liters_then_x(col_vs, id_col[d][q]))

    return cnf, id_row, id_col, g, m, variable_count


def get_cnf_variables(
    matrix_initial,
    ag,
    qubits,
    qubits_ori_to_reduce,
    qubits_reduce_to_ori,
    target_depth,
    disabled=[],
    min_num_q_compile=np.inf,
    max_num_variables=np.inf,
    print_info=False,
):
    num_q = len(qubits)
    # obtain connectivity information
    ag_sub = nx.subgraph(ag, qubits)
    # nx.draw(ag_sub, with_labels=1)
    # print("begin_matrix", matrix_initial)
    # print("qubits", qubits)
    edges = []
    for edge in ag_sub.edges:
        edges.append(
            (qubits_ori_to_reduce[edge[0]], qubits_ori_to_reduce[edge[1]])
        )
    t1 = time.time()
    variable_count = 0
    m = np.empty((target_depth + 1, num_q, num_q), dtype="int")
    for i in range(m.size):
        variable_count += 1
        m.flat[i] = variable_count
    g = []
    for d in range(target_depth):
        g.append({})
        for q0, q1 in edges:
            variable_count += 1
            g[d][(q0, q1)] = int(variable_count)
            variable_count += 1
            g[d][(q1, q0)] = int(variable_count)
    if variable_count > max_num_variables:
        raise ()
    assump = []
    disable_depths = []
    for d, q in disabled:
        if d > target_depth - 1:
            continue
        q = qubits_ori_to_reduce[q]
        if d not in disable_depths:
            disable_depths.append(d)
        for q0, q1 in edges:
            if q in (q0, q1):
                assump.append(-1 * g[d][(q0, q1)])
                assump.append(-1 * g[d][(q1, q0)])

    # generate variables for approximate methods to mark whether a row/column in matrix of a specific depth is equal to unit vector
    id_row, id_col = [], []
    if True:
        for d in range(target_depth + 1):
            id_row.append([])
            id_col.append([])
            for q in range(num_q):
                variable_count += 1
                id_row[d].append(int(variable_count))
                variable_count += 1
                id_col[d].append(int(variable_count))

    # init constraint
    cnf = CNF()
    # set constraint C1: each depth must have at least one gate
    # if the depth (time slot) has disabled potitions, we allow it not to have any gate.
    for d in range(target_depth):
        if d in disable_depths:
            continue
        cnf_add = []
        for q0, q1 in edges:
            cnf_add.extend([g[d][(q0, q1)], g[d][(q1, q0)]])
        cnf.append(cnf_add)

    # set revised constraint C2
    for d in range(target_depth):
        for c in range(num_q):
            variables_ = []
            for t in ag_sub.adj[qubits_reduce_to_ori[c]]:
                t = qubits_ori_to_reduce[t]
                variables_.extend([g[d][(c, t)], g[d][(t, c)]])
            cnf.extend(
                CardEnc.atmost(
                    lits=variables_, bound=1, encoding=EncType.pairwise
                )
            )
    # set constraint C3
    for d in range(target_depth):
        for c in range(num_q):
            for t in ag_sub.adj[qubits_reduce_to_ori[c]]:
                t = qubits_ori_to_reduce[t]
                cnf_add = []
                for j in range(num_q):
                    cnf_add.extend(
                        xor_equal(m[d][t][j], m[d][c][j], m[d + 1][t][j])
                    )
                if_c_then(g[d][(c, t)], cnf_add)
                cnf.extend(cnf_add)
    # set constraint C4
    for d in range(target_depth):
        for t in range(num_q):
            for j in range(num_q):
                variables_ = []
                for c in ag_sub.adj[qubits_reduce_to_ori[t]]:
                    c = qubits_ori_to_reduce[c]
                    variables_.append(g[d][(c, t)])
                if len(variables_) == 0:
                    print("target_depth", d, "num_q_t", t, "num_q_j", j)
                    print("qubits_ori_to_reduce", qubits_ori_to_reduce)
                    print("ag_sub", ag_sub.edges())
                    print("variables_", variables_)
                cnf_add = CardEnc.equals(
                    lits=variables_, bound=1, encoding=EncType.pairwise
                ).clauses
                if_x_neq_y_then(m[d + 1][t][j], m[d][t][j], cnf_add)
                cnf.extend(cnf_add)

    ## method2: make all rows & columns of the matrix in the final depth = unit vector
    if min_num_q_compile >= num_q:
        ### make sure all variables in id_row and id_col are True
        cnf.extend([[v] for v in id_row[target_depth]])
        cnf.extend([[v] for v in id_col[target_depth]])
    else:
        ### make sure some rows & columns of the matrix in the final depth = unit vector
        id_row_col_fin = []
        for q in range(num_q):
            variable_count += 1
            id_row_col_fin.append(int(variable_count))
        for q in range(num_q):
            cnf.extend(
                and_equal(
                    id_row[target_depth][q],
                    id_col[target_depth][q],
                    id_row_col_fin[q],
                )
            )
        cnf_add = CardEnc.atleast(
            lits=id_row_col_fin,
            bound=min_num_q_compile,
        )
        cnf.extend(cnf_add)

    # make m variables in depth 0 equal initial matrix
    for i in range(num_q):
        for j in range(num_q):
            cnf_add = CardEnc.equals(
                lits=[int(m[0][i][j])],
                bound=int(matrix_initial[i][j]),
                encoding=EncType.pairwise,
            )
            cnf.extend(cnf_add)

    if True:
        depth_start = min(
            int(START_DEPTH_RATIO * target_depth + 1), target_depth - 1
        )
        for d in range(depth_start, target_depth + 1):
            for q in range(num_q):
                raw_vs, col_vs = [], []
                for i, v in enumerate(m[d][q][:]):
                    v = int(v)
                    if i != q:
                        raw_vs.append(-1 * v)
                        cnf.append([-1 * v, -1 * id_row[d][q]])
                    else:
                        raw_vs.append(v)
                        cnf.append([v, -1 * id_row[d][q]])
                cnf.extend(if_liters_then_x(raw_vs, id_row[d][q]))
                for i, v in enumerate(m[d, :, q]):
                    v = int(v)
                    if i != q:
                        col_vs.append(-1 * v)
                        cnf.append([-1 * v, -1 * id_col[d][q]])
                    else:
                        col_vs.append(v)
                        cnf.append([v, -1 * id_col[d][q]])
                cnf.extend(if_liters_then_x(col_vs, id_col[d][q]))

    cnf_list = cnf.clauses
    for clause in cnf_list:
        for i in range(len(clause)):
            clause[i] = int(clause[i])
    cnf = CNF(from_clauses=cnf_list)
    if print_info:
        print(
            "Time cost for init. {} variables is {}".format(
                str(variable_count), str(time.time() - t1)
            )
        )

    return cnf, assump, g, m, variable_count, ag_sub, edges, num_q


def recompile_cx_yq_dis(
    cx_list,
    ag,
    target_depth,
    disabled_pos=[],
    dis_left=[],
    dis_right=[],
    solver_name="g41",  #'m22', 'g41'
    max_num_variables=np.inf,
    min_num_q_compile=np.inf,
    max_time=300,  # seconds
    print_info=False,
):
    sorted_dis = sorted(disabled_pos, key=lambda x: x[0])
    first_elements = {x[0] for x in sorted_dis}
    depth_min = len(first_elements)
    if target_depth < depth_min:
        return [], [], False, 0, 0, 0

    Sat_times = 0
    sorted_dis_right = sorted(dis_right, key=lambda x: x[0])
    depth_right = len({x[0] for x in sorted_dis_right})
    sorted_dis_left = sorted(dis_left, key=lambda x: x[0])
    depth_left = len({x[0] for x in sorted_dis_left})

    qubits = []
    for cx in cx_list:
        for q in cx:
            if q not in qubits:
                qubits.append(q)
    qubits.sort()
    num_q = len(qubits)
    qubits_ori_to_reduce, qubits_reduce_to_ori = {}, {}

    for i, q in enumerate(qubits):
        qubits_ori_to_reduce[q] = i
        qubits_reduce_to_ori[i] = q
    # generate target identity matrix
    matrix_target = np.eye(num_q)
    # generate initial matrix
    matrix_initial = np.eye(num_q, dtype="bool")
    cx_list_r = cx_list.copy()
    cx_list_r.reverse()
    for q_c, q_t in cx_list_r:
        q_c, q_t = qubits_ori_to_reduce[q_c], qubits_ori_to_reduce[q_t]
        matrix_initial[q_t] = np.logical_xor(
            matrix_initial[q_c], matrix_initial[q_t]
        )
    # obtain connectivity information
    ag_sub = nx.subgraph(ag, qubits)
    # nx.draw(ag_sub, with_labels=1)

    cnf, assump, g, m, variable_count, ag_sub, edges, num_q = (
        get_cnf_variables(
            matrix_initial,
            ag,
            qubits,
            qubits_ori_to_reduce,
            qubits_reduce_to_ori,
            target_depth,
            disabled_pos,
            min_num_q_compile=min_num_q_compile,
            max_num_variables=max_num_variables,
            print_info=print_info,
        )
    )
    num_cnf = len(cnf.clauses)
    assump = []
    t1 = time.time()
    with Solver(name=solver_name, bootstrap_with=cnf) as solver:
        min_depth = max(1, depth_left - 1)  # number of activated depths
        num_act_depth = target_depth - 1
        new_dis_left = [(item[0], item[1]) for item in dis_left]

        if len(dis_right) != 0:
            right_max_depth = max(item[0] for item in dis_right)
        else:
            right_max_depth = 0
        diff = right_max_depth - num_act_depth
        # new_dis_right = [(right_max_depth - item[0], item[1]) for item in dis_right]
        new_dis_right = [(item[0] - diff, item[1]) for item in dis_right]

        dis_range = depth_right
        for dis_offset in range(dis_range + 1):
            dis_right_new = [
                (item[0] + dis_offset, item[1])
                for item in new_dis_right
                if (item[0] + dis_offset) < target_depth
            ]
            new_dis_pos = dis_right_new + new_dis_left
            assump = []
            for d, q in new_dis_pos:
                if d > num_act_depth:
                    raise ()
                q = qubits_ori_to_reduce[q]
                for q0, q1 in edges:
                    if q in (q0, q1):
                        assump.append(-1 * g[d][(q0, q1)])
                        assump.append(-1 * g[d][(q1, q0)])
            flag = solver.solve_limited(
                assumptions=assump, expect_interrupt=True
            )
            Sat_times += 1
            if flag == True:
                break
        if print_info:
            print("formula is", f"{'s' if flag else 'uns'}atisfiable")

        sat_res = solver.get_model()

    if sat_res == None:
        return [], [], False, Sat_times, variable_count, num_cnf

    #  to final matrix
    d = target_depth
    matrix_final = np.ones((num_q, num_q)) * 2
    for i in range(num_q):
        for j in range(num_q):
            for v in sat_res:
                if m[d][i][j] == abs(v):
                    if v > 0:
                        matrix_final[i][j] = 1
                    else:
                        matrix_final[i][j] = 0
                    break

    cx_list, cx_list_depth = [], []
    for d in range(target_depth):
        cx_depth = []
        for c in range(num_q):
            for t in ag_sub.adj[qubits_reduce_to_ori[c]]:
                t = qubits_ori_to_reduce[t]
                for v in sat_res:
                    if g[d][(c, t)] == int(v):
                        if v > 0:
                            cx_new = (
                                qubits_reduce_to_ori[c],
                                qubits_reduce_to_ori[t],
                            )
                            cx_depth.append(cx_new)
                            cx_list.append(cx_new)
                        break
        cx_list_depth.append(cx_depth)

    return cx_list, cx_list_depth, flag, Sat_times, variable_count, num_cnf


def recompile_cx_yq(
    cx_list,
    ag,
    min_depth=1,
    max_depth=None,
    disabled_pos=[],
    dis_left=[],
    dis_right=[],
    solver_name="g41",
    max_num_variables=np.inf,
    min_num_q_compile=np.inf,
    max_time=300,
    print_info=False,
):
    if max_depth == 0:
        return [], [], False, 0, 0, 0
    Sat_total_times = 0
    variable_total = 0
    cnf_total = 0
    for d in range(max_depth):
        # print("d+1 is", d+1)
        if d + 1 < min_depth:
            continue
        (
            cx_list_re,
            cx_list_depth_re,
            flag,
            Sat_times,
            variable_count,
            num_cnf,
        ) = recompile_cx_yq_dis(
            cx_list,
            ag,
            d + 1,
            disabled_pos=disabled_pos,
            dis_left=dis_left,
            dis_right=dis_right,
            solver_name="g41",  #'m22', 'g41'
            max_num_variables=max_num_variables,
            min_num_q_compile=min_num_q_compile,
            max_time=max_time,  # seconds
            print_info=print_info,
        )
        Sat_total_times += Sat_times
        variable_total += variable_count
        cnf_total += num_cnf
        if len(cx_list_re) > 0:
            break
        if flag == None:
            break

    return (
        cx_list_re,
        cx_list_depth_re,
        flag,
        Sat_total_times,
        variable_total,
        cnf_total,
    )


def recompile_cx_yq_predict(
    cx_list,
    ag,
    min_depth=1,
    max_depth=None,
    predict_depth=None,
    disabled_pos=[],
    dis_left=[],
    dis_right=[],
    solver_name="g41",
    max_num_variables=np.inf,
    min_num_q_compile=np.inf,
    max_time=300,
    print_info=False,
):
    if max_depth == 0 or predict_depth > max_depth:
        return [], [], False, 0, 0, 0
    Sat_total_times = 0
    variable_total = 0
    cnf_total = 0
    d = 0
    for d in range(predict_depth, max_depth + 1):
        res = recompile_cx_yq_dis(
            cx_list,
            ag,
            d,
            disabled_pos=disabled_pos,
            dis_left=dis_left,
            dis_right=dis_right,
            solver_name="g41",  #'m22', 'g41'
            max_num_variables=max_num_variables,
            min_num_q_compile=min_num_q_compile,
            max_time=max_time,  # seconds
            print_info=print_info,
        )
        (
            cx_list_re,
            cx_list_depth_re,
            flag,
            Sat_times,
            variable_count,
            num_cnf,
        ) = res
        Sat_total_times += Sat_times
        variable_total += variable_count
        cnf_total += num_cnf
        if len(cx_list_re) > 0:
            break

    if d == predict_depth:
        for d in range(predict_depth - 1, 1, -1):
            res = recompile_cx_yq_dis(
                cx_list,
                ag,
                d,
                disabled_pos=disabled_pos,
                dis_left=dis_left,
                dis_right=dis_right,
                solver_name="g41",  #'m22', 'g41'
                max_num_variables=max_num_variables,
                min_num_q_compile=min_num_q_compile,
                max_time=max_time,  # seconds
                print_info=print_info,
            )
            (
                cx_list_re_new,
                cx_list_depth_re_new,
                flag,
                Sat_times,
                variable_count,
                num_cnf,
            ) = res
            Sat_total_times += Sat_times
            variable_total += variable_count
            cnf_total += num_cnf
            if len(cx_list_depth_re_new) != 0:
                cx_list_depth_re = deepcopy(cx_list_depth_re_new)
                cx_list_re = deepcopy(cx_list_re_new)
            else:
                break

    return (
        cx_list_re,
        cx_list_depth_re,
        flag,
        Sat_total_times,
        variable_total,
        cnf_total,
    )
