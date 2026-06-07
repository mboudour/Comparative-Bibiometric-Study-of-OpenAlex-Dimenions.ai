import os
import sys
import argparse
import pickle
import networkx as nx
from pyvis.network import Network

try:
    import pygraphviz  # noqa: F401
    HAS_PYGRAPHVIZ = True
except ImportError:
    HAS_PYGRAPHVIZ = False

GRAPH_DIR = "nx_graphs"
VIS_DIR = "pyvis_graphs"
os.makedirs(VIS_DIR, exist_ok=True)

NODE_SIZE = 5  # constant node size for all graphs

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
# Use --no_labels to hide node labels (label shown only on hover):
#   python visualize_biblio_graphs.py coauthorship_norm_w0_d0.pkl --no_labels
#
# Recommended node range for comfortable PyVis interaction: 70–130 nodes.
# For untruncated graphs, use --no_labels and expect slow rendering above ~5000 nodes.
# =============================================================================

# Maps filename prefixes to human-readable graph type names
GRAPH_TYPE_LABELS = {
    "coauthorship":           "Co-authorship Network",
    "bibliographic_coupling": "Bibliographic Coupling Network",
    "concept_cooccurrence":   "Concept Co-occurrence Network",
    "field_sharing":          "Research Field Sharing Network",
}

def make_title(pkl_filename, min_degree):
    """Build a human-readable title from the filename and threshold."""
    base = os.path.splitext(pkl_filename)[0]
    # Identify graph type
    graph_type = "Network"
    for prefix, label in GRAPH_TYPE_LABELS.items():
        if base.startswith(prefix):
            graph_type = label
            break
    # Normalized or raw?
    norm = "Normalized" if "_norm_" in base else "Raw"
    # Threshold info
    if min_degree > 0:
        threshold_str = f"  |  Degree threshold: {min_degree}"
    else:
        threshold_str = "  |  No degree threshold (full graph)"
    return f"{graph_type} — {norm}{threshold_str}"


def visualize_graph(pkl_filename, min_degree=0.0, no_labels=True):
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
    suffix = ""
    if min_degree > 0:
        suffix += f"_d{min_degree}"
    if no_labels:
        suffix += "_nolabels"
    html_filename = f"{base}{suffix}_vis.html"
    html_path = os.path.join(VIS_DIR, html_filename)

    # Build graph title
    title = make_title(pkl_filename, min_degree)

    # Collect edge weights for scaling
    all_weights = [d.get('weight', 1.0) for u, v, d in G.edges(data=True)]
    max_weight = max(all_weights) if all_weights else 1.0
    if max_weight == 0:
        max_weight = 1.0

    # Weighted degree for hover tooltip
    w_degrees = dict(G.degree(weight='weight'))

    # Compute layout positions using pygraphviz neato (Graphviz force-directed)
    # Falls back to NetworkX spring_layout if pygraphviz is not available.
    if HAS_PYGRAPHVIZ:
        pos = nx.nx_agraph.graphviz_layout(G, prog='neato')
    else:
        pos = nx.spring_layout(G, seed=42)

    # Scale positions to a 1000x1000 canvas for PyVis
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = (x_max - x_min) or 1.0
    y_range = (y_max - y_min) or 1.0
    scale = 1000.0
    pos_scaled = {
        n: ((pos[n][0] - x_min) / x_range * scale - scale / 2,
            (pos[n][1] - y_min) / y_range * scale - scale / 2)
        for n in pos
    }

    # cdn_resources="in_line" embeds all JS — no broken lib/ path.
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="black",
                  cdn_resources="in_line")

    # Add nodes — constant size, fixed positions from graphviz layout
    for node in G.nodes():
        wdeg = w_degrees.get(node, 0)
        node_label = "" if no_labels else str(node)
        x, y = pos_scaled.get(node, (0, 0))
        net.add_node(node,
                     label=node_label,
                     title=f"{node}\nWeighted degree: {wdeg:.4f}",
                     size=NODE_SIZE,
                     x=x, y=y,
                     physics=False)

    # Add edges with width scaled to weight
    for u, v, data in G.edges(data=True):
        w = data.get('weight', 1.0)
        if w is None or (isinstance(w, float) and w != w):
            w = 1.0
        width = 0.5 + 4.5 * (w / max_weight)
        net.add_edge(u, v, value=float(w), width=width, title=f"weight: {w:.4f}")

    # Physics disabled by default; configure panel for interactive adjustment
    net.set_options("""
    {
      "configure": {
        "enabled": true,
        "filter": ["physics", "nodes", "edges"]
      },
      "nodes": {
        "font": {
          "size": 0
        }
      },
      "physics": {
        "enabled": false
      }
    }
    """)

    # Inject the title as an H2 above the network canvas by post-processing the HTML
    net.save_graph(html_path)
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    title_html = (
        f'<h2 style="font-family:Arial,sans-serif;text-align:center;'
        f'margin:10px 0 4px 0;font-size:16px;color:#333;">{title}</h2>\n'
    )
    # Hide node labels: patch the options JSON inside the drawGraph function
    # so font size is 0 before the network is ever drawn.
    import re
    # Find the options = {...} block inside drawGraph and inject font size 0
    html = re.sub(
        r'(var options = \{)',
        r'\1\n    "nodes": {"font": {"size": 0, "color": "rgba(0,0,0,0)"}},',
        html
    )
    html = html.replace("<body>", "<body>\n" + title_html, 1)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

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
    parser.add_argument(
        "--no_labels", action="store_true",
        help="Hide node labels. Node name shown only on hover. "
             "Useful for large untruncated graphs."
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
        visualize_graph(pkl_filename, min_degree=args.min_degree, no_labels=args.no_labels)

    print("Done.")
