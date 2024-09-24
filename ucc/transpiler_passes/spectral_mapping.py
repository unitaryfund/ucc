import numpy as np
from scipy.linalg import eigh, orthogonal_procrustes
from scipy.optimize import linear_sum_assignment

from qiskit.transpiler.basepasses import AnalysisPass


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

        # Step 1: Extract the adjacency matrix of the coupling list
        target_adj = adjacency_matrix_from_list(self.coupling_list)

        # Step 2: Extract the adjacency matrix of the input circuit
        interaction_adj = adjacency_matrix_from_dag(dag)

        # Step 3: Perform spectral graph matching between the two adjacency matrices
        P = spectral_graph_matching(interaction_adj, target_adj)

        # Step 4: Convert the soft permutation matrix into a strict binary permutation matrix
        P = get_permutation_matrix(P)

        # Step 5: Convert the permutation matrix into a list
        virtual_to_physical_match = np.argmax(P, axis=1).tolist()

        return virtual_to_physical_match

def spectral_graph_matching(adj1, adj2, top_k=None):
    """
    Perform spectral graph matching between two graphs of unequal sizes.

    Parameters:
    adj1 (np.array): Adjacency matrix of graph 1
    adj2 (np.array): Adjacency matrix of graph 2
    top_k (int): Number of top eigenvectors to use (optional)

    Returns:
    P (np.array): Permutation matrix that aligns adj1 and adj2
    """
    # Step 1: Pad the smaller adjacency matrix to match the size of the larger one
    n1, n2 = adj1.shape[0], adj2.shape[0]
    if n1 < n2:
        adj1 = pad_adjacency_matrix(adj1, n2)
    elif n2 < n1:
        adj2 = pad_adjacency_matrix(adj2, n1)

    # Step 2: Compute eigenvalues and eigenvectors of adjacency matrices
    eigvals1, eigvecs1 = eigh(adj1)
    eigvals2, eigvecs2 = eigh(adj2)

    # Step 3: Optionally, select the top_k eigenvectors (ignoring smallest eigenvalues)
    if top_k:
        idx1 = np.argsort(eigvals1)[-top_k:]  # Top-k eigenvalues for graph 1
        idx2 = np.argsort(eigvals2)[-top_k:]  # Top-k eigenvalues for graph 2
        eigvecs1 = eigvecs1[:, idx1]
        eigvecs2 = eigvecs2[:, idx2]

    # Step 4: Use Procrustes analysis to align the eigenvectors
    R, _ = orthogonal_procrustes(eigvecs1, eigvecs2)

    # Step 5: Compute the permutation matrix
    P = eigvecs1 @ R @ eigvecs2.T

    return P

    
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
    
def get_permutation_matrix(P):
    """
    Convert the soft permutation matrix into a strict binary permutation matrix
    using the Hungarian algorithm.

    Parameters:
    P (np.array): The soft permutation matrix from spectral matching.

    Returns:
    np.array: A binary permutation matrix.
    """
    row_ind, col_ind = linear_sum_assignment(-P)  # Minimize negative P (maximize P)

    # Initialize a binary permutation matrix
    perm_matrix = np.zeros_like(P)
    perm_matrix[row_ind, col_ind] = 1

    return perm_matrix

def adjacency_matrix_from_dag(dag):

    # Step 1: Initialize an empty adjacency matrix
    num_qubits = dag.num_qubits
    adj_matrix = np.zeros((num_qubits, num_qubits), dtype=int)

    # Step 

            
def pad_adjacency_matrix(adj, target_size):
    """
    Pad an adjacency matrix with zeros to match the target size.

    Parameters:
    adj (np.array): Adjacency matrix to pad
    target_size (int): Target size (should be larger than adj.shape[0])

    Returns:
    np.array: Padded adjacency matrix
    """
    current_size = adj.shape[0]
    if current_size >= target_size:
        return adj  # No padding needed

    padded_adj = np.zeros((target_size, target_size))
    padded_adj[:current_size, :current_size] = adj
    return padded_adj