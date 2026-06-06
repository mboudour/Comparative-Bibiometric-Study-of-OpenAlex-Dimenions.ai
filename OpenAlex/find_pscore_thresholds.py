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
import networkx as nx

GRAPH_DIR = "nx_graphs"
TARGET_MIN = 70
TARGET_MAX = 130


def extract_ps_core(G, t):
    """Maximal subgraph where every node has weighted degree >= t."""
    core = G.copy()
    while True:
        to_remove = [n for n in core.nodes()
                     if sum(d.get('weight', 1.0) for _, _, d in core.edges(n, data=True)) < t]
        if not to_remove:
            break
        core.remove_nodes_from(to_remove)
    return core


def find_threshold(G):
    """Binary search for t giving TARGET_MIN <= nodes <= TARGET_MAX."""
    n_full = G.number_of_nodes()
    if n_full <= TARGET_MAX:
        return None, n_full  # plot as-is

    # Collect all unique weighted degrees as candidate thresholds
    wdeg_vals = sorted(set(
        sum(d.get('weight', 1.0) for _, _, d in G.edges(n, data=True))
        for n in G.nodes()
    ))

    # Binary search over sorted weighted degree values
    lo, hi = 0, len(wdeg_vals) - 1
    best_t = None
    best_n = n_full

    while lo <= hi:
        mid = (lo + hi) // 2
        t = wdeg_vals[mid]
        core = extract_ps_core(G, t)
        n = core.number_of_nodes()

        if TARGET_MIN <= n <= TARGET_MAX:
            best_t = t
            best_n = n
            break
        elif n > TARGET_MAX:
            lo = mid + 1   # need higher threshold to reduce nodes
        else:
            hi = mid - 1   # too few nodes, lower threshold

    # If exact range not found, find closest above TARGET_MIN
    if best_t is None:
        for t in reversed(wdeg_vals):
            core = extract_ps_core(G, t)
            n = core.number_of_nodes()
            if n >= TARGET_MIN:
                best_t = t
                best_n = n
                break

    return best_t, best_n


graphs = sorted([f for f in os.listdir(GRAPH_DIR) if f.endswith(".pkl")])

for fname in graphs:
    path = os.path.join(GRAPH_DIR, fname)
    with open(path, "rb") as f:
        G = pickle.load(f)

    n = G.number_of_nodes()
    e = G.number_of_edges()

    if n <= TARGET_MAX:
        print(f"{fname}: {n} nodes — plot as-is (no threshold needed)")
        continue

    print(f"{fname}: {n} nodes, {e} edges — searching...", flush=True)
    t, n_result = find_threshold(G)
    if t is None:
        print(f"  No threshold found — plot as-is ({n_result} nodes)")
    else:
        print(f"  Ps-core threshold t >= {t:.6f}  →  {n_result} nodes")
    print()
