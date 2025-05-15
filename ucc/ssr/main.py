#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 15:46:57 2024

@author: yunqihuang
"""

import networkx as nx
from copy import deepcopy
import numpy as np
import joblib
import time
import pandas as pd
from openpyxl import Workbook
import os
import multiprocessing
import random
import argparse

from ucc.ssr.genetic_swap_depth_opt_yq_ver import (
    genetic_opt,
    equivalence_checking,
)

import sys

# sys.path.append('../')
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

from ucc.ssr.circuittransform.inputs.cir_dg_swap_depth_opt import DGSwap
from ucc.ssr.circuittransform.inputs.ag import GenerateArchitectureGraph


def apply_operations(n, operations):
    M = np.eye(n)
    for operation in operations:
        row, col = operation
        M[col] = np.bitwise_xor(M[row].astype(int), M[col].astype(int)).astype(
            float
        )

    M = M.astype(int)
    return M


def get_neighbors(graph, nodes, num_to_select):
    # print("num to select", num_to_select)
    selected_neighbors = []
    all_selected_nodes = deepcopy(nodes)
    remain_select_num = deepcopy(num_to_select)
    while len(selected_neighbors) < num_to_select:
        all_neighbors = set()
        for node in all_selected_nodes:
            neighbors = set(graph.neighbors(node))
            all_neighbors.update(neighbors)
        # print("first all neightbors", all_neighbors)
        # print("nodes", nodes)
        all_neighbors = all_neighbors - set(nodes) - set(selected_neighbors)
        neighbors = list(all_neighbors)
        # print("neighbor", neighbors)
        round_select = random.sample(
            neighbors, min(remain_select_num, len(neighbors))
        )
        selected_neighbors.extend(round_select)
        remain_select_num -= len(round_select)
        all_selected_nodes.extend(selected_neighbors)
        # print(selected_neighbors)
    return selected_neighbors


def graph_model_dic():
    graph_model = dict()

    cycle = nx.Graph()
    cycle.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)])
    graph_model[cycle] = "q5cycle.pkl"

    path = nx.Graph()
    path.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
    graph_model[path] = "q5path.pkl"

    grid_with_line = nx.Graph()
    grid_with_line.add_edges_from([(0, 1), (1, 2), (2, 3), (0, 3), (0, 4)])
    graph_model[grid_with_line] = "q5grid_with_line.pkl"

    grid_2tri_line1 = nx.Graph()
    grid_2tri_line1.add_edges_from(
        [(0, 1), (1, 2), (2, 3), (0, 3), (0, 2), (0, 4)]
    )
    graph_model[grid_2tri_line1] = "q5grid_2tri_line1.pkl"

    grid_2tri_line2 = nx.Graph()
    grid_2tri_line2.add_edges_from(
        [(0, 1), (1, 2), (2, 3), (0, 3), (0, 2), (1, 4)]
    )
    graph_model[grid_2tri_line2] = "q5grid_2tri_line2.pkl"

    grid_x_line = nx.Graph()
    grid_x_line.add_edges_from(
        [(0, 1), (1, 2), (2, 3), (0, 3), (0, 2), (1, 3), (0, 4)]
    )
    graph_model[grid_x_line] = "q5grid_x_line.pkl"

    _2tri_x = nx.Graph()
    _2tri_x.add_edges_from([(0, 1), (0, 2), (1, 2), (0, 3), (0, 4), (3, 4)])
    graph_model[_2tri_x] = "q5grid_2tri_line1.pkl"

    tri_2line = nx.Graph()
    tri_2line.add_edges_from([(0, 1), (0, 2), (1, 2), (1, 3), (3, 4)])
    graph_model[tri_2line] = "q5tri_2line.pkl"

    t = nx.Graph()
    t.add_edges_from([(0, 1), (1, 2), (1, 3), (3, 4)])
    graph_model[t] = "q5T.pkl"

    ten = nx.Graph()
    ten.add_edges_from([(0, 1), (1, 2), (1, 3), (1, 4)])
    graph_model[ten] = "q5Ten.pkl"

    tri_2line_2 = nx.Graph()
    tri_2line_2.add_edges_from([(0, 1), (1, 2), (1, 3), (1, 4), (2, 4)])
    graph_model[tri_2line_2] = "q5tri_2line_2.pkl"

    tri_square = nx.Graph()
    tri_square.add_edges_from([(0, 1), (0, 3), (1, 2), (2, 3), (1, 4), (2, 4)])
    graph_model[tri_square] = "q5tri_square.pkl"

    complete = nx.complete_graph(5)
    graph_model[complete] = "q5total.pkl"

    return graph_model


def find_model(dg, node):
    graph_model = graph_model_dic()
    qubits = dg.nodes[node]["qubits"]
    # print("first qubit", qubits)
    qubits_list = deepcopy(qubits)
    if len(qubits_list) < 5:
        extend_qubits = get_neighbors(dg.ag, qubits_list, 5 - len(qubits_list))
        # print("extend_qubit", extend_qubits)
        qubits_list.extend(extend_qubits)
    # print("then qubit",qubits_list)
    subgraph = dg.ag.subgraph(qubits_list)
    # print(subgraph.edges())
    mapping = None
    for graph, model in graph_model.items():
        GM = nx.algorithms.isomorphism.GraphMatcher(subgraph, graph)
        # print("graph", graph.edges())
        if GM.is_isomorphic():
            mapping = GM.mapping
            final_model = model
            break
    if mapping == None:
        print(dg.nodes[node])
        print(dg.ag.edges())
        print(qubits_list)
        print(subgraph.edges())
        raise ()
    return mapping, final_model


def get_predict(dg, node):
    mapping, model_name = find_model(dg, node)
    cx_list = dg.get_node_cx_list(node)
    cx_map_list = [[mapping[cx[0]], mapping[cx[1]]] for cx in cx_list]
    M = apply_operations(5, cx_map_list)
    matrix_flatten = M.flatten()
    columns = ["F{}".format(i) for i in range(5 * 5)]
    test_df = pd.DataFrame([[*matrix_flatten]], columns=columns)
    model = joblib.load(
        "/Users/mistywahl/Documents/GitHub/ucc/ucc/ssr/ML_model/" + model_name
    )
    predict = model.predict(test_df)
    return predict


def get_node_score_predict(dg_new, repeated_node=[]):
    node_score = {}
    SAT_times = 0
    V_count = 0
    cnf_count = 0
    for node in dg_new.nodes:
        if node == dg_new.root or dg_new.nodes[node] in repeated_node:
            continue
        if dg_new.nodes[node]["num_gate_2q"] > 1:
            or_depth = dg_new.get_node_depth(node)
            if or_depth > 1:
                predict = get_predict(dg_new, node)
                score = or_depth - predict
                node_score[node] = score

    return node_score, SAT_times, V_count, cnf_count


def compile_sat_sweeping_num(dg, compile_ratio=0, compile_num=1, file_name=""):
    dg_new = deepcopy(dg)
    dg_test = dg_new.break_all_nodes(decompose_swap=False)
    dg_test.add_depth_to_all_edges()
    dg_test.add_swap_node()
    dg_depth = dg_test.depth
    get_node_time_log = []
    Sat_times = 0
    total_variable = 0
    cnf_total = 0
    time_node_b = time.time()
    node_score, S_times, V_count, cnf_count = get_node_score_predict(dg_new)
    time_node_end = time.time()
    get_node_time_log.append(time_node_end - time_node_b)
    Sat_times += S_times
    total_variable += V_count
    cnf_total += cnf_count
    repeated_node = []
    times = 0
    if compile_ratio > 0:
        compile_num = int(len(node_score) * compile_ratio)

    iterative_log = []
    depth_log = []
    iterative_times = 0
    iterative_log.append(iterative_times)
    depth_log.append(dg_depth)
    time_compile_log = []
    time_genetic_log = []
    time_compile_log.append(0)
    time_genetic_log.append(0)
    while node_score:
        node_score = {k: v for k, v in node_score.items() if v > 0}
        if len(node_score) == 0:
            break
        if len(node_score) <= compile_num:
            compile_node = list(node_score.keys())
        else:
            compile_node = [
                k
                for k, v in sorted(
                    node_score.items(), key=lambda item: item[1], reverse=True
                )[:compile_num]
            ]
        iterative_times += 1
        iterative_log.append(iterative_times)
        time_compile_before = time.time()
        for node in compile_node:
            predict_depth = round(get_predict(dg_new, node).item())

            flag, sat_time, variable_cout, num_cnf = (
                dg_new.recompile_cx_node_appro(
                    node, predict_depth=predict_depth, print_info=False
                )
            )
            Sat_times += sat_time
            total_variable += variable_cout
            cnf_total += num_cnf
            if flag == 0:
                repeated_node.append(dg_new.nodes[node])

        time_compile_after = time.time()
        time_compile_log.append(time_compile_after - time_compile_before)
        dg_new = dg_new.break_all_nodes(decompose_swap=False)
        dg_new.add_depth_to_all_edges()
        dg_new.add_swap_node()
        dg_depth_new = dg_new.depth
        depth_log.append(dg_depth_new)
        if dg_depth_new >= dg_depth:
            times += 1
        else:
            dg_depth = dg_depth_new
            times = 0
        if times > 5:
            break
        time_genetic_before = time.time()
        if len(dg_new.swap_nodes) != 0:
            dg_new = genetic_opt(
                0, dg_new, dg_new.ag, "depth", "cx", path=None
            )

        time_genetic_after = time.time()
        time_genetic_log.append(time_genetic_after - time_genetic_before)
        dg_new = dg_new.combine_2q_gates_simple(combine_level=2)
        time_node_b = time.time()
        node_score, S_times, V_count, cnf_count = get_node_score_predict(
            dg_new, repeated_node=repeated_node
        )
        time_node_end = time.time()
        get_node_time_log.append(time_node_end - time_node_b)
        Sat_times += S_times
        total_variable += V_count
        cnf_total += cnf_count
        if compile_ratio > 0:
            compile_num = int(len(node_score) * compile_ratio)
            if compile_num < 5 and dg_depth > 200:
                compile_num = 5

    if len(time_genetic_log) < len(iterative_log):
        time_genetic_log.append(0)
    dg_new = dg_new.break_all_nodes(decompose_swap=True)
    dg_new.add_depth_to_all_edges()

    return (
        dg_new,
        Sat_times,
        total_variable,
        cnf_total,
        sum(time_compile_log),
        sum(time_genetic_log),
        sum(get_node_time_log),
        iterative_times,
    )


def run_functions(file, path, ag, basic_2_q_gate, method_cost_func, path_cir):
    if not file.endswith(".qasm"):
        return []
    max_q = 5

    data = []
    data.append(file)
    dg = DGSwap(ag, basic_2_q_gate, method_cost_func)
    dg.from_qasm(file, path=path)
    dg.num_q = len(ag)
    or_depth = nx.dag_longest_path_length(dg, weight="depth")
    data.append(or_depth)
    dg_gate_num = deepcopy(dg)
    dg_gate_num.decompose_swaps()
    or_gates = dg_gate_num.num_gate
    data.append(or_gates)
    dg.cx_to_swap()
    if len(dg.swap_nodes) != 0:
        dg_new = genetic_opt(
            0, dg, dg.ag, method_cost_func, basic_2_q_gate, path=path
        )

    dg_new = dg.combine_2q_gates_simple(max_q=max_q, combine_level=2)

    time2 = time.time()

    (
        dg0,
        sat_times0,
        total_variable0,
        cnf_total0,
        sum_compile_time,
        sum_genetic_time,
        sum_predict_time,
        iterative_times,
    ) = compile_sat_sweeping_num(dg_new, compile_ratio=0.2)
    time2_end = time.time()
    nr_depth0 = nx.dag_longest_path_length(dg0, weight="depth")
    eq = equivalence_checking(dg, dg0, dg.ag)
    if not eq:
        nr_depth0 = 0

    dg0.to_qasm(file_name=path_cir + file)
    nr_gates0 = dg0.num_gate
    # except:
    #    nr_depth0, nr_gates0, sat_times0, total_variable0, cnf_total0, time2_end = 0,0,0,0,0,0
    data.append(nr_depth0)
    data.append(nr_gates0)
    data.append(sat_times0)
    data.append(total_variable0)
    data.append(cnf_total0)
    data.append(time2_end - time2)
    data.append(sum_compile_time)
    data.append(sum_genetic_time)
    data.append(sum_predict_time)
    data.append(iterative_times)
    print(data)

    return data


def wrapper(args):
    return run_functions(*args)


def process_quantum_circuits(
    input_folder: str,
    method_AG: list,
    output_xlsx: str,
    output_qasm_folder: str,
):
    """
    Process quantum circuits for transformation and optimization.

    Parameters:
        input_folder (str): Path to the input folder containing QASM files.
        method_AG (list): Architecture graph type.
        output_xlsx (str): Path to save the output Excel file.
        output_qasm_folder (str): Folder path to save transformed QASM circuits.
    """

    # Generate architecture graph
    ag, _ = GenerateArchitectureGraph(method_AG)
    method_cost_func = "depth"
    basic_2_q_gate = "cx"

    # Prepare output Excel file
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "Name",
            "Original Depth",
            "Original Gates",
            "Transformed Depth",
            "Transformed Gates",
            "SAT Times",
            "Variable Count",
            "CNF Count",
            "Total Time",
            "iterative_times",
        ]
    )

    # Get list of QASM files
    files = [f for f in os.listdir(input_folder) if f.endswith(".qasm")]
    inputs = [
        (
            file,
            input_folder,
            ag,
            basic_2_q_gate,
            method_cost_func,
            output_qasm_folder,
        )
        for file in files
    ]

    # Parallel processing
    num_p = min(multiprocessing.cpu_count(), len(files))
    pool = multiprocessing.Pool(processes=num_p)
    results = pool.map(wrapper, inputs)
    pool.close()
    pool.join()

    # Save results to Excel
    for res in results:
        ws.append(res)
    wb.save(output_xlsx)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        metavar="S",
        type=str,
        help="the path of the input circuits",
        default="Data/RevLib/Sabre/",
    )
    parser.add_argument(
        "--ag_type",
        type=str,
        help="the type of AG graph (sycamore, qgrid, rochester, heron)",
        default="qgrid",
    )
    parser.add_argument(
        "--qgrid_params",
        nargs=2,
        type=int,
        metavar=("ROWS", "COLS"),
        help="Specify the grid dimensions if -ag_type is qgrid.",
        default=[5, 4],
    )
    parser.add_argument(
        "--path_excel",
        type=str,
        help="The path of output excel data",
        default="Results/RevLib/Sabre/",
    )
    parser.add_argument(
        "--save_name",
        type=str,
        help="The name of excel data",
        default="qgrid_revlib_sabre",
    )
    parser.add_argument(
        "--path_cir",
        type=str,
        help="The path of output circuits",
        default="Results/RevLib/Sabre/",
    )

    args = parser.parse_args()

    if args.ag_type == "sycamore":
        method_AG = ["Google Sycamore"]
    elif args.ag_type == "qgrid":
        if not args.qgrid_params:
            parser.error(
                "The -qgrid_params must be provided when -ag_type is 'qgrid'."
            )
        else:
            rows, cols = args.qgrid_params
            method_AG = [f"Grid {rows}*{cols}"]
    elif args.ag_type == "heron":
        method_AG = ["IBM Heron"]
    elif args.ag_type == "rochester":
        method_AG = ["IBM Rochester"]

    input_folder = args.path

    output_xlsx = args.path_excel + args.save_name + ".xlsx"

    output_qasm_folder = args.path_cir

    process_quantum_circuits(
        input_folder, method_AG, output_xlsx, output_qasm_folder
    )
