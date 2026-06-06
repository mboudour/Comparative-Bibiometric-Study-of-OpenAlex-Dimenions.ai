"""
find_pscore_thresholds.py
Finds the Ps-core threshold t that yields 70–130 nodes for each graph in nx_graphs/.

Uses the Batagelj-Zaveršnik O(m) peeling algorithm:
  - Compute weighted degree for all nodes once.
  - Peel nodes in order of increasing weighted degree, updating neighbours.
  - Record each node's Ps-core level (its weighted degree at time of removal).
  - Find threshold giving 70–130 nodes by a single sorted lookup.

Run from the OpenAlex/ (or Dimensions/) folder:
    python find_pscore_thresholds.py

Paste the output into the chat so run_pscore_visualizations.py can be written.
"""

import os
import pickle

GRAPH_DIR = "nx_graphs"
TARGET_MIN = 70
TARGET_MAX = 130


def ps_core_decomposition(G):
    """
    Batagelj-Zaveršnik O(m) weighted core decomposition.
    Returns a dict {node: ps_core_level} where ps_core_level is the
    weighted degree of the node at the time it was peeled.
    Nodes that survive to the end get the final weighted degree as their level.
    """
    # Build weighted adjacency as plain dicts for speed
    wdeg = {}
    adj = {n: {} for n in G.nodes()}
    for u, v, d in G.edges(data=True):
        w = d.get('weight', 1.0)
        if w is None or w != w:  # None or NaN
            w = 1.0
        adj[u][v] = w
        adj[v][u] = w
        wdeg[u] = wdeg.get(u, 0.0) + w
        wdeg[v] = wdeg.get(v, 0.0) + w

    core_level = {}
    active = set(G.nodes())

    # Use a simple sorted-list peeling (efficient enough for O(m) amortised)
    import heapq
    heap = [(wdeg.get(n, 0.0), n) for n in active]
    heapq.heapify(heap)

    in_heap = {n: True for n in active}

    while heap:
        w, n = heapq.heappop(heap)
        if n not in active:
            continue
        # Lazy deletion: skip if stale entry
        if abs(wdeg.get(n, 0.0) - w) > 1e-12:
            heapq.heappush(heap, (wdeg[n], n))
            continue
        # Peel node n
        core_level[n] = wdeg.get(n, 0.0)
        active.remove(n)
        for nb, ew in adj[n].items():
            if nb in active:
                wdeg[nb] -= ew
                heapq.heappush(heap, (wdeg[nb], nb))

    return core_level


def find_threshold_for_target(core_level, target_min, target_max):
    """Given core levels, find threshold t such that target_min <= |{n: level>=t}| <= target_max."""
    levels = sorted(core_level.values(), reverse=True)
    n_total = len(levels)

    if n_total <= target_max:
        return None, n_total  # plot as-is

    # levels[i] is the (i+1)-th highest core level
    # Keeping nodes with level >= levels[i] gives (i+1) nodes
    # We want index closest to target_max
    if len(levels) >= target_max:
        t_max = levels[target_max - 1]
        n_at_tmax = sum(1 for l in levels if l >= t_max)
    else:
        t_max = 0
        n_at_tmax = n_total

    if len(levels) >= target_min:
        t_min = levels[target_min - 1]
        n_at_tmin = sum(1 for l in levels if l >= t_min)
    else:
        t_min = 0
        n_at_tmin = n_total

    return t_max, n_at_tmax, t_min, n_at_tmin


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

    print(f"  {n} nodes, {e} edges — decomposing...", flush=True)
    core_level = ps_core_decomposition(G)

    result = find_threshold_for_target(core_level, TARGET_MIN, TARGET_MAX)
    if result[0] is None:
        print(f"  No threshold needed — {result[1]} nodes")
    else:
        t_max, n_at_tmax, t_min, n_at_tmin = result
        print(f"  Ps-core threshold >= {t_max:.4f}  →  {n_at_tmax} nodes  (use for ~{TARGET_MAX} nodes)")
        print(f"  Ps-core threshold >= {t_min:.4f}  →  {n_at_tmin} nodes  (use for ~{TARGET_MIN} nodes)")
