"""
find_pscore_thresholds.py
Finds the Ps-core threshold t that yields 70–130 nodes for each graph in nx_graphs/.

Run from the OpenAlex/ (or Dimensions/) folder:
    python find_pscore_thresholds.py

Paste the output into the chat so run_pscore_visualizations.py can be written
with the correct threshold values.
"""

import os
import pickle
import numpy as np

GRAPH_DIR = "nx_graphs"
TARGET_MIN = 70
TARGET_MAX = 130
N_CANDIDATES = 200   # number of threshold candidates to sample


def extract_ps_core(G, t, wdeg_cache=None):
    """Maximal subgraph where every node has weighted degree >= t.
    Uses an efficient iterative removal with a node-degree dict."""
    # Build weighted degree dict
    wdeg = {}
    for u, v, d in G.edges(data=True):
        w = d.get('weight', 1.0) or 1.0
        wdeg[u] = wdeg.get(u, 0.0) + w
        wdeg[v] = wdeg.get(v, 0.0) + w

    # Start with all nodes
    active = set(G.nodes())
    # Build adjacency with weights for fast removal
    adj = {n: {} for n in active}
    for u, v, d in G.edges(data=True):
        w = d.get('weight', 1.0) or 1.0
        adj[u][v] = w
        adj[v][u] = w

    # Iteratively remove nodes below threshold
    queue = [n for n in active if wdeg.get(n, 0.0) < t]
    while queue:
        n = queue.pop()
        if n not in active:
            continue
        active.remove(n)
        for nb, w in adj[n].items():
            if nb in active:
                wdeg[nb] -= w
                if wdeg[nb] < t:
                    queue.append(nb)

    return len(active)


def find_threshold(G, fname):
    n_full = G.number_of_nodes()
    if n_full <= TARGET_MAX:
        return None, n_full

    print(f"  Computing weighted degrees...", flush=True)
    # Compute weighted degree for all nodes
    wdeg = {}
    for u, v, d in G.edges(data=True):
        w = d.get('weight', 1.0) or 1.0
        wdeg[u] = wdeg.get(u, 0.0) + w
        wdeg[v] = wdeg.get(v, 0.0) + w

    all_wdeg = sorted(wdeg.values())
    w_min = all_wdeg[0]
    w_max = all_wdeg[-1]

    # Sample N_CANDIDATES thresholds geometrically between w_min and w_max
    if w_min <= 0:
        w_min = 1e-9
    candidates = np.geomspace(w_min, w_max, N_CANDIDATES).tolist()
    candidates = sorted(set([round(c, 8) for c in candidates]))

    print(f"  Searching {len(candidates)} threshold candidates...", flush=True)

    best_t = None
    best_n = 0

    # Binary search over candidates
    lo, hi = 0, len(candidates) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        t = candidates[mid]
        n = extract_ps_core(G, t)
        if TARGET_MIN <= n <= TARGET_MAX:
            best_t = t
            best_n = n
            break
        elif n > TARGET_MAX:
            lo = mid + 1
        else:
            hi = mid - 1

    # If not found in sampled candidates, do a fine search around the closest point
    if best_t is None:
        # Find the candidate where n crosses TARGET_MAX from above
        # by scanning from high to low
        for t in reversed(candidates):
            n = extract_ps_core(G, t)
            if n >= TARGET_MIN:
                best_t = t
                best_n = n
                break

    return best_t, best_n


graphs = sorted([f for f in os.listdir(GRAPH_DIR) if f.endswith(".pkl")])

for fname in graphs:
    path = os.path.join(GRAPH_DIR, fname)
    print(f"\n{fname}", flush=True)
    with open(path, "rb") as f:
        G = pickle.load(f)

    n = G.number_of_nodes()
    e = G.number_of_edges()

    if n <= TARGET_MAX:
        print(f"  {n} nodes — plot as-is (no threshold needed)")
        continue

    print(f"  {n} nodes, {e} edges — searching...", flush=True)
    t, n_result = find_threshold(G, fname)
    if t is None:
        print(f"  No threshold found — plot as-is ({n_result} nodes)")
    else:
        print(f"  Ps-core threshold t >= {t:.6f}  →  {n_result} nodes")
