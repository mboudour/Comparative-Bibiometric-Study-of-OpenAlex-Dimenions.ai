"""
compare_centrality.py
---------------------
Centrality rank correlation between OpenAlex and Dimensions networks.

For each matching pair of graph types, this script:

  1. Identifies the aligned node intersection (nodes present in both databases,
     matched by node label / identifier string).
  2. Computes three centrality measures on each full graph:
       - Weighted degree centrality
       - Weighted PageRank
       - Betweenness centrality (on the aligned subgraph, for tractability)
  3. Restricts centrality vectors to the aligned intersection.
  4. Reports Spearman's ρ and Kendall's τ for each centrality measure.

Usage
-----
Run from the project root:
    python comparison/compare_centrality.py

Outputs:
  - comparison/centrality_results.csv  — correlation coefficients per graph type
"""

import os
import pickle
import pandas as pd
import networkx as nx
from scipy.stats import spearmanr, kendalltau

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OA_GRAPH_DIR  = os.path.join(os.path.dirname(__file__), '..', 'OpenAlex',   'nx_graphs')
DIM_GRAPH_DIR = os.path.join(os.path.dirname(__file__), '..', 'Dimensions', 'nx_graphs')
OUTPUT_CSV    = os.path.join(os.path.dirname(__file__), 'centrality_results.csv')

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

# Betweenness is expensive on large graphs; skip if node count exceeds this threshold
BETWEENNESS_NODE_LIMIT = 5000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_graph(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def corr_pair(vec_oa, vec_dim, nodes):
    """Return (spearman_r, spearman_p, kendall_tau, kendall_p) for aligned vectors."""
    v_oa  = [vec_oa[n]  for n in nodes]
    v_dim = [vec_dim[n] for n in nodes]
    sr, sp = spearmanr(v_oa, v_dim)
    kt, kp = kendalltau(v_oa, v_dim)
    return round(sr, 4), round(sp, 6), round(kt, 4), round(kp, 6)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def compare_pair(prefix):
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

    print(f"  Shared nodes: {len(shared_nodes)}")

    # Weighted degree centrality
    wdeg_oa  = {n: d for n, d in G_oa.degree(weight='weight')}
    wdeg_dim = {n: d for n, d in G_dim.degree(weight='weight')}
    deg_sr, deg_sp, deg_kt, deg_kp = corr_pair(wdeg_oa, wdeg_dim, shared_nodes)

    # PageRank
    pr_oa  = nx.pagerank(G_oa,  weight='weight')
    pr_dim = nx.pagerank(G_dim, weight='weight')
    pr_sr, pr_sp, pr_kt, pr_kp = corr_pair(pr_oa, pr_dim, shared_nodes)

    # Betweenness (on aligned subgraph only, for tractability)
    if len(shared_nodes) <= BETWEENNESS_NODE_LIMIT:
        sub_oa  = G_oa.subgraph(shared_nodes)
        sub_dim = G_dim.subgraph(shared_nodes)
        bc_oa  = nx.betweenness_centrality(sub_oa,  weight='weight', normalized=True)
        bc_dim = nx.betweenness_centrality(sub_dim, weight='weight', normalized=True)
        bc_sr, bc_sp, bc_kt, bc_kp = corr_pair(bc_oa, bc_dim, shared_nodes)
    else:
        print(f"  [INFO] Skipping betweenness (>{BETWEENNESS_NODE_LIMIT} shared nodes)")
        bc_sr = bc_sp = bc_kt = bc_kp = float('nan')

    return {
        'graph':           prefix,
        'shared_nodes':    len(shared_nodes),
        'deg_spearman_r':  deg_sr,  'deg_spearman_p':  deg_sp,
        'deg_kendall_tau': deg_kt,  'deg_kendall_p':   deg_kp,
        'pr_spearman_r':   pr_sr,   'pr_spearman_p':   pr_sp,
        'pr_kendall_tau':  pr_kt,   'pr_kendall_p':    pr_kp,
        'bc_spearman_r':   bc_sr,   'bc_spearman_p':   bc_sp,
        'bc_kendall_tau':  bc_kt,   'bc_kendall_p':    bc_kp,
    }


def main():
    rows = []
    for prefix in GRAPH_PREFIXES:
        print(f"Processing: {prefix}")
        result = compare_pair(prefix)
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
