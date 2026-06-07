"""
run_pscore_visualizations.py  —  Dimensions
Generates PyVis HTML visualisations for normalized graphs only.

Extraction method per graph type:
  - field_sharing:            full graph (70 nodes, no threshold needed)
  - co-authorship:            Ps-core (Batagelj-Zaveršnik) at ~70 nodes
  - bibliographic_coupling:   degree threshold at ~130 nodes
                              (Ps-core has a cliff: 666 nodes at t=100,
                               17 nodes at t=200 — no threshold gives ~70 nodes)
  - concept_cooccurrence:     Ps-core (Batagelj-Zaveršnik) at ~70 nodes

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

# Each entry: (pkl_filename, threshold, method, graph_type_label, norm_label)
# method: "pscore" or "degree"
CONFIGS = [
    ("field_sharing_norm_f0_d0.pkl",          0.0,      "pscore",  "Research Field Sharing Network",  "Normalized"),
    ("coauthorship_norm_w0_d0.pkl",           5.5333,   "pscore",  "Co-authorship Network",           "Normalized"),
    ("bibliographic_coupling_norm_r0_d0.pkl", 139.7165, "degree",  "Bibliographic Coupling Network",  "Normalized"),
    ("concept_cooccurrence_norm_c0_d0.pkl",   31.0,     "pscore",  "Concept Co-occurrence Network",   "Normalized"),
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
        if abs(wdeg.get(n, 0.0) - w) > 1e-12:
            heapq.heappush(heap, (wdeg[n], n))
            continue
        if wdeg.get(n, 0.0) >= t:
            break
        active.remove(n)
        for nb, ew in adj[n].items():
            if nb in active:
                wdeg[nb] -= ew
                heapq.heappush(heap, (wdeg[nb], nb))

    return G.subgraph(active).copy()


# ---------------------------------------------------------------------------
# Degree threshold extraction (weighted degree)
# ---------------------------------------------------------------------------
def extract_degree_threshold(G, t):
    """Return subgraph keeping only nodes with weighted degree >= t."""
    if t <= 0:
        return G
    wdeg = {n: sum(d.get('weight', 1.0) or 1.0 for _, _, d in G.edges(n, data=True))
            for n in G.nodes()}
    keep = [n for n, wd in wdeg.items() if wd >= t]
    return G.subgraph(keep).copy()


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------
def visualize(pkl_filename, threshold, method, graph_type_label, norm_label):
    pkl_path = os.path.join(GRAPH_DIR, pkl_filename)
    if not os.path.exists(pkl_path):
        print(f"  File not found: {pkl_path} — skipping.")
        return

    print(f"\n>>> {pkl_filename}  ({method} t={threshold})")
    with open(pkl_path, "rb") as f:
        G = pickle.load(f)

    if method == "pscore":
        G = extract_ps_core(G, threshold)
        method_label = f"Ps-core threshold: {threshold}"
        suffix = f"_ps{threshold}" if threshold > 0 else ""
    else:
        G = extract_degree_threshold(G, threshold)
        method_label = f"Degree threshold: {threshold}"
        suffix = f"_d{threshold}" if threshold > 0 else ""

    n, e = G.number_of_nodes(), G.number_of_edges()
    print(f"  After filter: Nodes: {n}, Edges: {e}")

    if n == 0:
        print("  No nodes — skipping.")
        return

    if e > 15000:
        print(f"  WARNING: {e} edges — this may be slow in the browser.")

    title = f"{graph_type_label} — {norm_label}  |  {method_label}"

    base      = os.path.splitext(pkl_filename)[0]
    html_path = os.path.join(VIS_DIR, f"{base}{suffix}_vis.html")

    all_weights = [d.get('weight', 1.0) or 1.0 for _, _, d in G.edges(data=True)]
    max_weight  = max(all_weights) if all_weights else 1.0

    w_degrees = {node: sum(d.get('weight', 1.0) or 1.0 for _, _, d in G.edges(node, data=True))
                 for node in G.nodes()}

    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black",
                  cdn_resources="in_line")

    for node in G.nodes():
        wd = w_degrees.get(node, 0)
        net.add_node(node,
                     label=str(node),
                     title=f"{node}\nWeighted degree: {wd:.4f}",
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
for cfg in CONFIGS:
    visualize(*cfg)

print("\nAll visualisations complete. HTMLs saved to pyvis_graphs/.")
