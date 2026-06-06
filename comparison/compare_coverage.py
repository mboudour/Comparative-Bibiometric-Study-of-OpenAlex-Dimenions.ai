"""
compare_coverage.py
-------------------
Coverage comparison between OpenAlex and Dimensions networks.

For each matching pair of graph types (co-authorship, bibliographic coupling,
concept co-occurrence, field sharing), this script computes:

  - Node counts and overlap (intersection / union = Jaccard)
  - Directed node overlap: fraction of OA nodes also in Dimensions, and vice versa
  - Edge counts and overlap (Jaccard on aligned node intersection)
  - Directed edge overlap: fraction of OA edges also in Dimensions, and vice versa
  - Spearman correlation of edge weights on shared edges

Nodes are aligned using the node label (string identifier) as the common key.
For co-authorship networks this is the author name/ID; for bibliographic coupling
it is the paper ID; for concept co-occurrence it is the concept label; for field
sharing it is the field label.

Usage
-----
Run from the project root:
    python comparison/compare_coverage.py

Outputs a summary table to stdout and saves results to comparison/coverage_results.csv.
"""

import os
import pickle
import glob
import itertools
import pandas as pd
import networkx as nx
from scipy.stats import spearmanr

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OA_GRAPH_DIR  = os.path.join(os.path.dirname(__file__), '..', 'OpenAlex',    'nx_graphs')
DIM_GRAPH_DIR = os.path.join(os.path.dirname(__file__), '..', 'Dimensions',  'nx_graphs')
OUTPUT_CSV    = os.path.join(os.path.dirname(__file__), 'coverage_results.csv')

# Graph type prefixes to compare (matched by prefix across both folders)
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_graph(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return float('nan')
    return len(set_a & set_b) / len(set_a | set_b)


def directed_overlap(set_a, set_b):
    """Fraction of set_a elements also in set_b."""
    if not set_a:
        return float('nan')
    return len(set_a & set_b) / len(set_a)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def compare_pair(prefix):
    oa_path  = os.path.join(OA_GRAPH_DIR,  prefix + '.pkl')
    dim_path = os.path.join(DIM_GRAPH_DIR, prefix + '.pkl')

    if not os.path.exists(oa_path):
        print(f"  [SKIP] OpenAlex file not found: {oa_path}")
        return None
    if not os.path.exists(dim_path):
        print(f"  [SKIP] Dimensions file not found: {dim_path}")
        return None

    G_oa  = load_graph(oa_path)
    G_dim = load_graph(dim_path)

    nodes_oa  = set(G_oa.nodes())
    nodes_dim = set(G_dim.nodes())
    nodes_shared = nodes_oa & nodes_dim

    # Edge sets on the full graphs
    edges_oa  = set(frozenset(e[:2]) for e in G_oa.edges())
    edges_dim = set(frozenset(e[:2]) for e in G_dim.edges())

    # Edge sets restricted to shared nodes
    edges_oa_shared  = set(frozenset(e[:2]) for e in G_oa.edges()
                           if e[0] in nodes_shared and e[1] in nodes_shared)
    edges_dim_shared = set(frozenset(e[:2]) for e in G_dim.edges()
                           if e[0] in nodes_shared and e[1] in nodes_shared)

    # Weight correlation on edges present in both (within shared nodes)
    common_edges = edges_oa_shared & edges_dim_shared
    weight_corr = float('nan')
    if len(common_edges) >= 5:
        w_oa  = []
        w_dim = []
        for e in common_edges:
            u, v = tuple(e)
            w_oa.append( G_oa[u][v].get('weight', 1.0))
            w_dim.append(G_dim[u][v].get('weight', 1.0))
        rho, _ = spearmanr(w_oa, w_dim)
        weight_corr = rho

    return {
        'graph':               prefix,
        'nodes_oa':            len(nodes_oa),
        'nodes_dim':           len(nodes_dim),
        'nodes_shared':        len(nodes_shared),
        'node_jaccard':        round(jaccard(nodes_oa, nodes_dim), 4),
        'node_overlap_oa':     round(directed_overlap(nodes_oa, nodes_dim), 4),
        'node_overlap_dim':    round(directed_overlap(nodes_dim, nodes_oa), 4),
        'edges_oa':            len(edges_oa),
        'edges_dim':           len(edges_dim),
        'edges_shared':        len(common_edges),
        'edge_jaccard':        round(jaccard(edges_oa_shared, edges_dim_shared), 4),
        'edge_overlap_oa':     round(directed_overlap(edges_oa_shared, edges_dim_shared), 4),
        'edge_overlap_dim':    round(directed_overlap(edges_dim_shared, edges_oa_shared), 4),
        'weight_spearman_r':   round(weight_corr, 4) if weight_corr == weight_corr else float('nan'),
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
