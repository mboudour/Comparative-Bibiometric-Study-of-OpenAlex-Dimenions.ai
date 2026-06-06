import os
import sys
import argparse
import pickle
import networkx as nx
from pyvis.network import Network

GRAPH_DIR = "nx_graphs"
VIS_DIR = "pyvis_graphs"
os.makedirs(VIS_DIR, exist_ok=True)

# =============================================================================
# USAGE
# Run without arguments to visualise ALL .pkl files in nx_graphs/:
#   python visualize_biblio_graphs.py
#
# Run with one or more filenames to visualise specific graphs only:
#   python visualize_biblio_graphs.py coauthorship_norm_w0_d0.pkl
#
# Use --min_degree to filter nodes before visualising (keeps top-degree nodes):
#   python visualize_biblio_graphs.py coauthorship_norm_w0_d0.pkl --min_degree 19.46
#
# Recommended node range for comfortable PyVis interaction: 70–130 nodes.
# =============================================================================

def visualize_graph(pkl_filename, min_degree=0.0):
    pkl_path = os.path.join(GRAPH_DIR, pkl_filename)
    if not os.path.exists(pkl_path):
        print(f"  File not found: {pkl_path} — skipping.")
        return

    print(f"Loading {pkl_filename}...")
    with open(pkl_path, "rb") as f:
        G = pickle.load(f)

    # Apply weighted degree filter if requested
    if min_degree > 0:
        nodes_to_keep = [n for n, d in G.degree(weight='weight') if d >= min_degree]
        G = G.subgraph(nodes_to_keep).copy()
        print(f"  After degree filter (weighted >= {min_degree}): Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    else:
        print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    if n_nodes == 0:
        print(f"  No nodes after filtering — skipping.")
        return

    if n_nodes > 5000 or n_edges > 50000:
        print(f"  WARNING: This graph is very large ({n_nodes} nodes, {n_edges} edges) "
              f"and may freeze or crash the browser.")

    # Build output filename
    base = os.path.splitext(pkl_filename)[0]
    if min_degree > 0:
        html_filename = f"{base}_d{min_degree}_vis.html"
    else:
        html_filename = f"{base}_vis.html"
    html_path = os.path.join(VIS_DIR, html_filename)

    # Compute weighted degree for node sizing
    w_degrees = dict(G.degree(weight='weight'))
    max_wdeg = max(w_degrees.values()) if w_degrees else 1.0
    if max_wdeg == 0:
        max_wdeg = 1.0

    # Collect all edge weights for scaling
    all_weights = [d.get('weight', 1.0) for u, v, d in G.edges(data=True)]
    max_weight = max(all_weights) if all_weights else 1.0
    if max_weight == 0:
        max_weight = 1.0

    # cdn_resources="in_line" embeds all JS into the HTML — no external lib/ folder needed.
    # This ensures the file opens correctly from any location.
    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="black",
                  select_menu=True, filter_menu=True, cdn_resources="in_line")

    # Add nodes explicitly with size scaled to weighted degree
    for node in G.nodes():
        wdeg = w_degrees.get(node, 0)
        size = 5 + 40 * (wdeg / max_wdeg)
        label = str(node)
        net.add_node(node, label=label, title=f"{label}\nWeighted degree: {wdeg:.4f}", size=size)

    # Add edges explicitly with width scaled to weight
    for u, v, data in G.edges(data=True):
        w = data.get('weight', 1.0)
        if w is None or (isinstance(w, float) and w != w):
            w = 1.0
        width = 0.5 + 4.5 * (w / max_weight)
        net.add_edge(u, v, value=float(w), width=width, title=f"weight: {w:.4f}")

    net.show_buttons(filter_=['physics', 'nodes', 'edges'])

    # Disable physics by default so graph renders immediately; user can enable via panel
    net.set_options("""
    {
      "physics": {
        "enabled": false
      }
    }
    """)

    net.save_graph(html_path)
    print(f"  Saved: {html_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Visualise pickled NetworkX graphs using PyVis."
    )
    parser.add_argument(
        "graphs", nargs="*",
        help="One or more .pkl filenames from nx_graphs/ to visualise. "
             "If omitted, all .pkl files in nx_graphs/ are visualised."
    )
    parser.add_argument(
        "--min_degree", type=float, default=0.0,
        help="Minimum weighted degree threshold. Use values from find_thresholds.py."
    )
    args = parser.parse_args()

    if args.graphs:
        targets = args.graphs
    else:
        targets = sorted([f for f in os.listdir(GRAPH_DIR) if f.endswith(".pkl")])
        if not targets:
            print(f"No .pkl files found in {GRAPH_DIR}/. Run create_biblio_graphs.py first.")
            sys.exit(0)
        print(f"No specific files given. Visualising all {len(targets)} graph(s) in {GRAPH_DIR}/.")

    for pkl_filename in targets:
        visualize_graph(pkl_filename, min_degree=args.min_degree)

    print("Done.")
