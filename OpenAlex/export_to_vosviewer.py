"""
export_to_vosviewer.py
Exports all NetworkX graphs in nx_graphs/ to VOSviewer-compatible text files.

For each .pkl file, two files are written to vosviewer_files/:
  - <name>_map.txt    : node map file  (id, label, weight)
  - <name>_network.txt: network file   (source id, target id, strength)

Run from the OpenAlex/ (or Dimensions/) folder:
    python export_to_vosviewer.py

Then open VOSviewer and load the pair of files for any graph you want to visualise.
"""

import os
import pickle

GRAPH_DIR = "nx_graphs"
OUT_DIR = "vosviewer_files"
os.makedirs(OUT_DIR, exist_ok=True)

graphs = sorted([f for f in os.listdir(GRAPH_DIR) if f.endswith(".pkl")])

for fname in graphs:
    path = os.path.join(GRAPH_DIR, fname)
    base = os.path.splitext(fname)[0]

    print(f"Exporting {fname}...")
    with open(path, "rb") as f:
        G = pickle.load(f)

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    print(f"  Nodes: {n_nodes}, Edges: {n_edges}")

    # --- Map file (nodes) ---
    map_path = os.path.join(OUT_DIR, f"{base}_map.txt")
    w_degrees = dict(G.degree(weight='weight'))
    with open(map_path, "w", encoding="utf-8") as mf:
        mf.write("id\tlabel\tweight\n")
        for i, node in enumerate(G.nodes(), start=1):
            label = str(node).replace("\t", " ").replace("\n", " ")
            wdeg = w_degrees.get(node, 0.0)
            if wdeg is None or (isinstance(wdeg, float) and wdeg != wdeg):
                wdeg = 0.0
            mf.write(f"{i}\t{label}\t{wdeg:.6f}\n")
    print(f"  Map file:     {base}_map.txt")

    # Build node-to-id mapping for the network file
    node_to_id = {node: i for i, node in enumerate(G.nodes(), start=1)}

    # --- Network file (edges) ---
    net_path = os.path.join(OUT_DIR, f"{base}_network.txt")
    with open(net_path, "w", encoding="utf-8") as nf:
        nf.write("source id\ttarget id\tstrength\n")
        for u, v, data in G.edges(data=True):
            w = data.get('weight', 1.0)
            if w is None or (isinstance(w, float) and w != w):
                w = 1.0
            src = node_to_id[u]
            tgt = node_to_id[v]
            nf.write(f"{src}\t{tgt}\t{w:.6f}\n")
    print(f"  Network file: {base}_network.txt")

print(f"\nDone. All files written to {OUT_DIR}/")
