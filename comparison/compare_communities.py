"""
compare_communities.py
----------------------
Community structure comparison between OpenAlex and Dimensions networks.

For each matching pair of graph types, this script:

  1. Runs Louvain community detection independently on each database's graph.
  2. Restricts the resulting partitions to the aligned node intersection.
  3. Computes Normalised Mutual Information (NMI) and Adjusted Rand Index (ARI)
     between the two partitions on the shared nodes.

Usage
-----
Run from the project root:
    python comparison/compare_communities.py

Requires: python-louvain (community) and scikit-learn.
Install with: pip install python-louvain scikit-learn

Outputs:
  - comparison/community_results.csv  — NMI and ARI per graph type
"""

import os
import pickle
import pandas as pd
import networkx as nx

try:
    import community as community_louvain
except ImportError:
    raise ImportError("Install python-louvain: pip install python-louvain")

from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OA_GRAPH_DIR  = os.path.join(os.path.dirname(__file__), '..', 'OpenAlex',   'nx_graphs')
DIM_GRAPH_DIR = os.path.join(os.path.dirname(__file__), '..', 'Dimensions', 'nx_graphs')
OUTPUT_CSV    = os.path.join(os.path.dirname(__file__), 'community_results.csv')

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

RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_graph(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def detect_communities(G):
    """Run Louvain on an undirected weighted graph; return partition dict {node: community_id}."""
    if G.is_directed():
        G = G.to_undirected()
    return community_louvain.best_partition(G, weight='weight', random_state=RANDOM_SEED)

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
    if len(shared_nodes) < 10:
        print(f"  [SKIP] Fewer than 10 shared nodes for: {prefix}")
        return None

    print(f"  Shared nodes: {len(shared_nodes)} — running Louvain...")

    part_oa  = detect_communities(G_oa)
    part_dim = detect_communities(G_dim)

    labels_oa  = [part_oa[n]  for n in shared_nodes]
    labels_dim = [part_dim[n] for n in shared_nodes]

    nmi = normalized_mutual_info_score(labels_oa, labels_dim, average_method='arithmetic')
    ari = adjusted_rand_score(labels_oa, labels_dim)

    n_comm_oa  = len(set(part_oa.values()))
    n_comm_dim = len(set(part_dim.values()))

    return {
        'graph':         prefix,
        'shared_nodes':  len(shared_nodes),
        'n_comm_oa':     n_comm_oa,
        'n_comm_dim':    n_comm_dim,
        'nmi':           round(nmi, 4),
        'ari':           round(ari, 4),
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
