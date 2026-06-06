"""
compare_qap.py
--------------
Quadratic Assignment Procedure (QAP) comparison between OpenAlex and Dimensions networks.

For each matching pair of graph types, this script:

  1. Identifies the aligned node intersection (nodes present in both databases).
  2. Constructs the weighted adjacency matrices restricted to the shared nodes.
  3. Applies QAP (Hubert & Schultz, 1976; Krackhardt, 1988):
       - Computes the Mantel correlation (Pearson r) between the two flattened
         upper-triangle adjacency vectors.
       - Generates a null distribution by permuting the rows and columns of one
         matrix N_PERMUTATIONS times and recomputing r each time.
       - Reports the observed r and the permutation p-value
         (fraction of permuted r values >= observed r).

References
----------
Hubert, L., & Schultz, J. (1976). Quadratic assignment as a general data analysis
  strategy. British Journal of Mathematical and Statistical Psychology, 29(2), 190-241.
Krackhardt, D. (1988). Predicting with networks: Nonparametric multiple regression
  analysis of dyadic data. Social Networks, 10(4), 359-381.

Limitation
----------
QAP assumes the node alignment is correct. Disambiguation errors in persistent
identifiers (e.g., ORCID) will cause the test to underestimate true structural
similarity between the databases.

Usage
-----
Run from the project root:
    python comparison/compare_qap.py

Outputs:
  - comparison/qap_results.csv  — Mantel r and permutation p-value per graph type
"""

import os
import pickle
import numpy as np
import pandas as pd
import networkx as nx
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OA_GRAPH_DIR  = os.path.join(os.path.dirname(__file__), '..', 'OpenAlex',   'nx_graphs')
DIM_GRAPH_DIR = os.path.join(os.path.dirname(__file__), '..', 'Dimensions', 'nx_graphs')
OUTPUT_CSV    = os.path.join(os.path.dirname(__file__), 'qap_results.csv')

GRAPH_PREFIXES = [
    'coauthorship_w0_d0',
    'coauthorship_norm_w0_d0',
    'bibliographic_coupling_r0_d0',
    'bibliographic_coupling_norm_r0_d0',
    'concept_cooccurrence_c0_d0',
    'concept_cooccurrence_norm_c0_d0',
    'field_sharing_f0_d0',
    'field_sharing_norm_f0_d0',
]

N_PERMUTATIONS = 1000   # increase to 10000 for publication-quality p-values
RANDOM_SEED    = 42

# QAP on very large aligned subgraphs is memory-intensive; skip if shared nodes exceed this
QAP_NODE_LIMIT = 10000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_graph(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def adjacency_vector(G, nodes):
    """Return the upper-triangle of the weighted adjacency matrix as a 1-D array."""
    n = len(nodes)
    idx = {v: i for i, v in enumerate(nodes)}
    mat = np.zeros((n, n), dtype=float)
    for u, v, d in G.edges(data=True):
        if u in idx and v in idx:
            w = d.get('weight', 1.0)
            mat[idx[u], idx[v]] = w
            mat[idx[v], idx[u]] = w
    # Upper triangle (excluding diagonal)
    triu_idx = np.triu_indices(n, k=1)
    return mat, mat[triu_idx]


def qap_test(mat_a, vec_a, vec_b, n_permutations, rng):
    """
    QAP permutation test.
    Permutes rows/columns of mat_a simultaneously and recomputes Pearson r with vec_b.
    Returns (observed_r, p_value).
    """
    n = mat_a.shape[0]
    triu_idx = np.triu_indices(n, k=1)

    observed_r, _ = pearsonr(vec_a, vec_b)

    count_ge = 0
    for _ in range(n_permutations):
        perm = rng.permutation(n)
        mat_perm = mat_a[np.ix_(perm, perm)]
        vec_perm = mat_perm[triu_idx]
        r_perm, _ = pearsonr(vec_perm, vec_b)
        if r_perm >= observed_r:
            count_ge += 1

    p_value = count_ge / n_permutations
    return observed_r, p_value

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def compare_pair(prefix, rng):
    oa_path  = os.path.join(OA_GRAPH_DIR,  prefix + '.pkl')
    dim_path = os.path.join(DIM_GRAPH_DIR, prefix + '.pkl')

    if not os.path.exists(oa_path) or not os.path.exists(dim_path):
        print(f"  [SKIP] Missing file for: {prefix}")
        return None

    G_oa  = load_graph(oa_path)
    G_dim = load_graph(dim_path)

    shared_nodes = sorted(set(G_oa.nodes()) & set(G_dim.nodes()))
    if len(shared_nodes) < 5:
        print(f"  [SKIP] Fewer than 5 shared nodes for: {prefix}")
        return None

    if len(shared_nodes) > QAP_NODE_LIMIT:
        print(f"  [SKIP] Too many shared nodes ({len(shared_nodes)} > {QAP_NODE_LIMIT}) for QAP — "
              f"reduce graph size with a higher threshold first.")
        return {
            'graph': prefix,
            'shared_nodes': len(shared_nodes),
            'mantel_r': float('nan'),
            'qap_p_value': float('nan'),
            'n_permutations': N_PERMUTATIONS,
            'note': f'skipped: >{QAP_NODE_LIMIT} shared nodes',
        }

    print(f"  Shared nodes: {len(shared_nodes)} — running QAP ({N_PERMUTATIONS} permutations)...")

    mat_oa,  vec_oa  = adjacency_vector(G_oa,  shared_nodes)
    mat_dim, vec_dim = adjacency_vector(G_dim, shared_nodes)

    # Permute OA matrix, correlate with DIM vector
    observed_r, p_value = qap_test(mat_oa, vec_oa, vec_dim, N_PERMUTATIONS, rng)

    return {
        'graph':          prefix,
        'shared_nodes':   len(shared_nodes),
        'mantel_r':       round(observed_r, 4),
        'qap_p_value':    round(p_value, 4),
        'n_permutations': N_PERMUTATIONS,
        'note':           '',
    }


def main():
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []
    for prefix in GRAPH_PREFIXES:
        print(f"Processing: {prefix}")
        result = compare_pair(prefix, rng)
        if result:
            rows.append(result)

    if not rows:
        print("No results — check that nx_graphs/ folders exist and contain .pkl files.")
        return

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nResults saved to: {OUTPUT_CSV}\n")
    print(df.to_string(index=False))


if __name__ == '__main__':
    main()
