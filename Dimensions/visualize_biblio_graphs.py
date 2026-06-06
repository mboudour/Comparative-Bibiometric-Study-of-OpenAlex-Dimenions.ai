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
#   python visualize_biblio_graphs.py coauthorship_norm_w0_d0.pkl bibliographic_coupling_norm_r0_d0.pkl
#
# Use --min_degree to filter nodes before visualising (keeps top-degree nodes):
#   python visualize_biblio_graphs.py coauthorship_norm_w0_d0.pkl --min_degree 19.46
#
# The output HTML is saved to pyvis_graphs/ with the same base name as the .pkl file,
# suffixed with the degree threshold used (e.g. coauthorship_norm_w0_d0_d19.46_vis.html).
#
# Indicative PyVis rendering times (modern browser, ~8 GB RAM):
#   < 500 nodes,  < 2,000 edges   → fast       (< 10 seconds)
#   < 2,000 nodes, < 10,000 edges → moderate   (10–60 seconds)
#   < 5,000 nodes, < 50,000 edges → slow       (1–5 minutes)
#   > 5,000 nodes or > 50,000 edges → may freeze or crash the browser
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

    # Apply degree filter if requested
    if min_degree > 0:
        nodes_to_keep = [n for n, d in G.degree() if d >= min_degree]
        G = G.subgraph(nodes_to_keep).copy()
        print(f"  After degree filter (>= {min_degree}): Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    else:
        print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    if n_nodes > 5000 or n_edges > 50000:
        print(f"  WARNING: This graph is very large ({n_nodes} nodes, {n_edges} edges) "
              f"and may freeze or crash the browser.")
        print(f"  Use --min_degree to reduce the graph size before visualising.")

    # Build output filename — include degree suffix if filtered
    base = os.path.splitext(pkl_filename)[0]
    if min_degree > 0:
        html_filename = f"{base}_d{min_degree}_vis.html"
    else:
        html_filename = f"{base}_vis.html"
    html_path = os.path.join(VIS_DIR, html_filename)

    # Initialize PyVis Network with white background and all interactive tools
    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="black",
                  select_menu=True, filter_menu=True)
    net.from_nx(G)
    net.show_buttons(filter_=['physics', 'nodes', 'edges'])

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
        help="Minimum node degree threshold. Nodes with degree below this value are removed "
             "before visualisation. Use the values from find_thresholds.py to target 70–130 nodes."
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
