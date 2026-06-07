"""
run_pscore_visualizations.py  —  Dimensions
Generates PyVis HTML visualisations using Ps-core extraction
(Batagelj-Zaveršnik O(m) peeling) at thresholds that yield ~130 nodes.

Run from the Dimensions/ folder:
    python run_pscore_visualizations.py
"""

import os
import pickle
import heapq
from pyvis.network import Network

GRAPH_DIR = "nx_graphs"
VIS_DIR   = "pyvis_graphs"
os.makedirs(VIS_DIR, exist_ok=True)

NODE_SIZE = 15  # constant size for all nodes

# Ps-core thresholds targeting ~70 nodes (from find_pscore_thresholds.py)
PSCORE_CONFIGS = [
    # (pkl_filename,                          ps_threshold,  graph_type_label,          norm_label)
    ("field_sharing_f0_d0.pkl",               0.0,    "Research Field Sharing Network",   "Raw"),
    ("field_sharing_norm_f0_d0.pkl",          0.0,    "Research Field Sharing Network",   "Normalized"),
    ("coauthorship_norm_w0_d0.pkl",           5.5333, "Co-authorship Network",            "Normalized"),
    ("coauthorship_w0_d0.pkl",                2698.0, "Co-authorship Network",            "Raw"),
    ("bibliographic_coupling_norm_r0_d0.pkl", 39.6311,"Bibliographic Coupling Network",   "Normalized"),
    ("bibliographic_coupling_r0_d0.pkl",      1184.0, "Bibliographic Coupling Network",   "Raw"),
    ("concept_cooccurrence_norm_c0_d0.pkl",   31.0,   "Concept Co-occurrence Network",    "Normalized"),
    ("concept_cooccurrence_c0_d0.pkl",        41104.0,"Concept Co-occurrence Network",    "Raw"),
]


# ---------------------------------------------------------------------------
# Ps-core extraction — Batagelj-Zaveršnik O(m) peeling
# ---------------------------------------------------------------------------
def extract_ps_core(G, t):
    """Return the subgraph of G where every node has weighted degree >= t."""
    if t <= 0:
        return G

    wdeg = {}
    adj  = {n: {} for n in G.nodes()}
    for u, v, d in G.edges(data=True):
        w = d.get('weight', 1.0)
        if w is None or (isinstance(w, float) and w != w):
            w = 1.0
        adj[u][v] = w
        adj[v][u] = w
        wdeg[u] = wdeg.get(u, 0.0) + w
        wdeg[v] = wdeg.get(v, 0.0) + w

    active = set(G.nodes())
    heap   = [(wdeg.get(n, 0.0), n) for n in active]
    heapq.heapify(heap)

    while heap:
        w, n = heapq.heappop(heap)
        if n not in active:
            continue
        if abs(wdeg.get(n, 0.0) - w) > 1e-12:          # stale entry
            heapq.heappush(heap, (wdeg[n], n))
            continue
        if wdeg.get(n, 0.0) >= t:
            break                                         # all remaining nodes qualify
        active.remove(n)
        for nb, ew in adj[n].items():
            if nb in active:
                wdeg[nb] -= ew
                heapq.heappush(heap, (wdeg[nb], nb))

    return G.subgraph(active).copy()


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------
def visualize(pkl_filename, ps_threshold, graph_type_label, norm_label):
    pkl_path = os.path.join(GRAPH_DIR, pkl_filename)
    if not os.path.exists(pkl_path):
        print(f"  File not found: {pkl_path} — skipping.")
        return

    print(f"\n>>> {pkl_filename}  (Ps-core t={ps_threshold})")
    with open(pkl_path, "rb") as f:
        G = pickle.load(f)

    G = extract_ps_core(G, ps_threshold)
    n, e = G.number_of_nodes(), G.number_of_edges()
    print(f"  After Ps-core (t >= {ps_threshold}): Nodes: {n}, Edges: {e}")

    if n == 0:
        print("  No nodes — skipping.")
        return

    # Build title
    if ps_threshold > 0:
        threshold_str = f"Ps-core threshold: {ps_threshold}"
    else:
        threshold_str = "No threshold (full graph)"
    title = f"{graph_type_label} — {norm_label}  |  {threshold_str}"

    # Output filename
    base   = os.path.splitext(pkl_filename)[0]
    suffix = f"_ps{ps_threshold}" if ps_threshold > 0 else ""
    html_path = os.path.join(VIS_DIR, f"{base}{suffix}_vis.html")

    # Edge weight scaling
    all_weights = [d.get('weight', 1.0) or 1.0 for _, _, d in G.edges(data=True)]
    max_weight  = max(all_weights) if all_weights else 1.0

    # Weighted degree for hover tooltip
    w_degrees = {n: sum(d.get('weight', 1.0) or 1.0 for _, _, d in G.edges(n, data=True))
                 for n in G.nodes()}

    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black",
                  cdn_resources="in_line")

    for node in G.nodes():
        wdeg = w_degrees.get(node, 0)
        net.add_node(node,
                     label=str(node),
                     title=f"{node}\nWeighted degree: {wdeg:.4f}",
                     size=NODE_SIZE)

    for u, v, data in G.edges(data=True):
        w = data.get('weight', 1.0)
        if w is None or (isinstance(w, float) and w != w):
            w = 1.0
        width = 0.5 + 4.5 * (w / max_weight)
        net.add_edge(u, v, value=float(w), width=width, title=f"weight: {w:.4f}")

    net.set_options("""
    {
      "configure": {
        "enabled": true,
        "filter": ["physics", "nodes", "edges"]
      },
      "physics": {
        "enabled": false
      }
    }
    """)

    net.save_graph(html_path)

    # Inject title above canvas
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    title_html = (
        f'<h2 style="font-family:Arial,sans-serif;text-align:center;'
        f'margin:10px 0 4px 0;font-size:16px;color:#333;">{title}</h2>\n'
    )
    html = html.replace("<body>", "<body>\n" + title_html, 1)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Saved: {os.path.basename(html_path)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
for cfg in PSCORE_CONFIGS:
    visualize(*cfg)

print("\nAll Ps-core visualisations complete. HTMLs saved to pyvis_graphs/.")
