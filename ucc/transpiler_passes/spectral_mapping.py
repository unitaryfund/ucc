import numpy as np

from scipy.linalg import eigh, orthogonal_procrustes
from scipy.optimize import linear_sum_assignment
import networkx as nx
import random

from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.transpiler import Layout


class SpectralMapping(AnalysisPass):
    """Map the circuit to the coupling map using spectral techniques."""

    def __init__(self, coupling_list):
        """
        Args:
            coupling_list: list of tuples representing the coupling map
        """
        super().__init__()
        self.coupling_list = coupling_list

    def run(self, dag):
        """Run the SpectralMapping pass on `dag`.

        Args: 
            dag (DAGCircuit): input dag
        """

        self.dag = dag
        num_qubits = self.dag.num_qubits()       
        
        # Extract a connected subgraph of the target adjacency matrix
        best_subgraph = greedy_connected_subgraph(self.coupling_list, num_qubits)
        best_subgraph_qubits = list(best_subgraph.nodes)
        best_subgraph_adj = nx.to_numpy_array(best_subgraph)

        # Extract the adjacency matrix of the input circuit
        circuit_adj = self._adjacency_matrix_from_dag()

        qubit_order = spectral_graph_matching(circuit_adj, best_subgraph_adj)

        # Reorder the qubits in the input circuit based on the matching using best_subgraph_qubits
        virtual_to_physical_match = {qubit:best_subgraph_qubits[qubit_order[i]] for i, qubit in enumerate(self.dag.qubits)}

        # Create a layout object
        layout = Layout(virtual_to_physical_match)
        for qreg in self.dag.qregs.values():
            layout.add_register(qreg)

        self.property_set["sabre_starting_layouts"] = [layout]

        return dag
    
    def _adjacency_matrix_from_dag(self):

        # Step 1: Initialize an empty adjacency matrix
        num_qubits = self.dag.num_qubits()
        qubit_indices = {qubit: index for index, qubit in enumerate(self.dag.qubits)}
        adj_matrix = np.zeros((num_qubits, num_qubits), dtype=int)

        # Step through dag
        for node in self.dag.op_nodes(include_directives=False):
            len_args = len(node.qargs)
            if len_args == 2:
                qargs = [qubit_indices[qubit] for qubit in node.qargs]
                adj_matrix[qargs[0], qargs[1]] += 1
                adj_matrix[qargs[1], qargs[0]] += 1

        return adj_matrix


def spectral_graph_matching(A, B):

    """
    Perform spectral graph matching between two graphs of equal sizes.
    Parameters:
    A (np.array): Adjacency matrix or Laplacian of graph 1
    B (np.array): Adjacency matrix or Laplacian of graph 2
    Returns:
    np.array: Index mapping from graph 1 to graph 2
    """
    #Ensure that the adjacency matrices are of the same size
    n1, n2 = A.shape[0], B.shape[0]
    if n1 != n2:
        raise ValueError("The adjacency matrices must be of the same size.")

    # Compute eigenvalues and eigenvectors of adjacency matrices
    A_eigenvals, A_eigenvecs = eigh(A)  
    B_eigenvals, B_eigenvecs = eigh(B)


    # Compute the similarity matrix
    P = np.zeros((n1, n1))
    eta = 0.1/np.log(n1)
    for i in range(n1):
        for j in range(n1):
            weight = eta / (eta**2 + (A_eigenvals[i] - B_eigenvals[j])**2)
            P += weight * np.outer(A_eigenvecs[:, i], B_eigenvecs[:, j])

    # Solve the linear assignment problem
    row_ind, col_ind = linear_sum_assignment(-P)

    return col_ind   




def adjacency_matrix_from_list(adj_list, num_nodes=None):
    """
    Construct an adjacency matrix from an adjacency list.

    Parameters:
    adj_list (list of lists): Each sublist contains two integers representing an edge (coupling) between two nodes.
    num_nodes (int): Total number of nodes in the graph.

    Returns:
    np.array: Adjacency matrix of shape (num_nodes, num_nodes).
    """

    # Step 0: Determine the number of nodes if not provided
    if not num_nodes:
        num_nodes = max([max(edge) for edge in adj_list]) + 1

    # Step 1: Initialize an empty adjacency matrix of size num_nodes x num_nodes
    adj_matrix = np.zeros((num_nodes, num_nodes), dtype=int)

    # Step 2: Populate the adjacency matrix based on the adjacency list
    for edge in adj_list:
        node1, node2 = edge
        adj_matrix[node1, node2] = 1
        adj_matrix[node2, node1] = 1  # Assuming an undirected graph

    return adj_matrix   


def greedy_connected_subgraph(coupling_list, subgraph_size):
    """
    Construct a connected subgraph of a graph based on a greedy algorithm.
    """
    
    G = nx.from_edgelist(coupling_list)

    if subgraph_size > len(G):
        raise ValueError("The subgraph size cannot exceed the number of nodes in the graph.")
    
    # Start with the highest connected node
    best_subgraph = set([max(dict(G.degree).items(), key=lambda x: x[1])[0]])   
    while len(best_subgraph) < subgraph_size:
        best_node = None
        best_edges = 0

        # Convert nodes to a list and shuffle
        nodes = list(G.nodes - best_subgraph)
        random.shuffle(nodes)
        
        for node in nodes:
            temp_subgraph = best_subgraph | {node}
            subgraph_edges = G.subgraph(temp_subgraph).number_of_edges()
            
            if subgraph_edges > best_edges:
                best_edges = subgraph_edges
                best_node = node
        
        if best_node is None:  # No node improved connectivity
            break
        
        best_subgraph.add(best_node)
    
    return G.subgraph(best_subgraph)