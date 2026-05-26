import os
import sys
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
#   python visualize_biblio_graphs.py coauthorship_w3_d2.pkl
#   python visualize_biblio_graphs.py coauthorship_w3_d2.pkl concept_cooccurrence_c10_d3.pkl
#
# The output HTML is saved to pyvis_graphs/ with the same base name as the .pkl file.
#
# Indicative PyVis rendering times (modern browser, ~8 GB RAM):
#   < 500 nodes,  < 2,000 edges  → fast       (< 10 seconds)
#   < 2,000 nodes, < 10,000 edges → moderate  (10–60 seconds)
#   < 5,000 nodes, < 50,000 edges → slow      (1–5 minutes)
#   > 5,000 nodes or > 50,000 edges → may freeze or crash the browser
#
# Use create_biblio_graphs.py with appropriate threshold parameters to produce
# graphs of a suitable size before visualising.
# =============================================================================

def visualize_graph(pkl_filename):
    pkl_path = os.path.join(GRAPH_DIR, pkl_filename)
    if not os.path.exists(pkl_path):
        print(f"  File not found: {pkl_path} — skipping.")
        return

    print(f"Loading {pkl_filename}...")
    with open(pkl_path, "rb") as f:
        G = pickle.load(f)

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    print(f"  Nodes: {n_nodes}, Edges: {n_edges}")

    if n_nodes > 5000 or n_edges > 50000:
        print(f"  WARNING: This graph is very large and may freeze or crash the browser.")
        print(f"  Consider re-running create_biblio_graphs.py with higher threshold values.")

    # Derive a human-readable title from the filename
    base = os.path.splitext(pkl_filename)[0]
    title = base.replace("_", " ").title()

    # Initialize PyVis Network with white background and all interactive tools
    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="black",
                  select_menu=True, filter_menu=True)
    net.from_nx(G)
    net.show_buttons(filter_=['physics', 'nodes', 'edges'])

    html_filename = f"{base}_vis.html"
    html_path = os.path.join(VIS_DIR, html_filename)
    net.save_graph(html_path)
    print(f"  Saved: {html_filename}")


if __name__ == "__main__":
    # If filenames are passed as arguments, visualise only those
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        # Otherwise visualise all .pkl files found in GRAPH_DIR
        targets = sorted([f for f in os.listdir(GRAPH_DIR) if f.endswith(".pkl")])
        if not targets:
            print(f"No .pkl files found in {GRAPH_DIR}/. Run create_biblio_graphs.py first.")
            sys.exit(0)
        print(f"No specific files given. Visualising all {len(targets)} graph(s) in {GRAPH_DIR}/.")

    for pkl_filename in targets:
        visualize_graph(pkl_filename)

    print("Done.")
