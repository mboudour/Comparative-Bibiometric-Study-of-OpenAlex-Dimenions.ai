import os
import pandas as pd
import networkx as nx
import pickle
from itertools import combinations

DATA_DIR = "data"
GRAPH_DIR = "nx_graphs"
os.makedirs(GRAPH_DIR, exist_ok=True)

# =============================================================================
# THRESHOLD PARAMETERS
# Adjust these values before running to control graph density.
# The chosen values are encoded in the output filename so multiple versions
# can coexist in nx_graphs/ without overwriting each other.
#
# Set any threshold to 0 to apply no filtering for that criterion.
#
# Indicative PyVis rendering times (modern browser, ~8 GB RAM):
#   < 500 nodes,  < 2,000 edges  → fast       (< 10 seconds)
#   < 2,000 nodes, < 10,000 edges → moderate  (10–60 seconds)
#   < 5,000 nodes, < 50,000 edges → slow      (1–5 minutes)
#   > 5,000 nodes or > 50,000 edges → may freeze or crash the browser
#
# Recommended starting thresholds for a corpus of ~40,000 articles:
#   Co-authorship:          MIN_COAUTH_WEIGHT = 3,  MIN_DEGREE = 2
#   Bibliographic Coupling: MIN_SHARED_REFS   = 5,  MIN_DEGREE = 2
#   Concept Co-occurrence:  MIN_CONCEPT_COOC  = 10, MIN_DEGREE = 3
#   Research Field Sharing: MIN_FIELD_COOC    = 10, MIN_DEGREE = 3
# =============================================================================

MIN_COAUTH_WEIGHT = 0   # Minimum co-authored papers for a co-authorship edge
MIN_SHARED_REFS   = 0   # Minimum shared references for a bibliographic coupling edge
MIN_CONCEPT_COOC  = 0   # Minimum co-occurrences for a concept co-occurrence edge
MIN_FIELD_COOC    = 0   # Minimum co-occurrences for a field sharing edge
MIN_DEGREE        = 0   # Minimum degree applied to all graphs after edge pruning


def apply_degree_filter(G, min_degree):
    if min_degree > 0:
        nodes_to_keep = [n for n, d in G.degree() if d >= min_degree]
        G = G.subgraph(nodes_to_keep).copy()
    return G


def save_graph(G, base_name, suffix):
    filename = f"{base_name}_{suffix}.pkl"
    path = os.path.join(GRAPH_DIR, filename)
    with open(path, "wb") as f:
        pickle.dump(G, f)
    print(f"  Saved: {filename}  (Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()})")


def create_coauthorship_graph():
    print("Creating Co-authorship graph...")
    edges_file = os.path.join(DATA_DIR, "openalex_coauth_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found. Run fetch_data.py first.")
        return

    df = pd.read_csv(edges_file)
    edge_weights = df.groupby(['source', 'target']).size().reset_index(name='weight')

    if MIN_COAUTH_WEIGHT > 0:
        edge_weights = edge_weights[edge_weights['weight'] >= MIN_COAUTH_WEIGHT]

    G = nx.Graph()
    for _, row in edge_weights.iterrows():
        G.add_edge(row['source'], row['target'], weight=int(row['weight']))

    G = apply_degree_filter(G, MIN_DEGREE)
    suffix = f"w{MIN_COAUTH_WEIGHT}_d{MIN_DEGREE}"
    save_graph(G, "coauthorship", suffix)


def create_bibliographic_coupling_graph():
    print("Creating Bibliographic Coupling graph...")
    edges_file = os.path.join(DATA_DIR, "openalex_bib_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    df = pd.read_csv(edges_file)

    B = nx.Graph()
    papers = df['paper_id'].unique()
    refs = df['reference_id'].unique()
    B.add_nodes_from(papers, bipartite=0)
    B.add_nodes_from(refs, bipartite=1)
    B.add_edges_from(zip(df['paper_id'], df['reference_id']))

    G = nx.bipartite.weighted_projected_graph(B, papers)

    if MIN_SHARED_REFS > 0:
        edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d.get('weight', 1) < MIN_SHARED_REFS]
        G.remove_edges_from(edges_to_remove)
        G.remove_nodes_from(list(nx.isolates(G)))

    G = apply_degree_filter(G, MIN_DEGREE)
    suffix = f"r{MIN_SHARED_REFS}_d{MIN_DEGREE}"
    save_graph(G, "bibliographic_coupling", suffix)


def create_concept_cooccurrence_graph():
    print("Creating Concept Co-occurrence graph...")
    edges_file = os.path.join(DATA_DIR, "openalex_concept_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    df = pd.read_csv(edges_file)
    grouped = df.groupby('paper_id')['concept_name'].apply(list)

    edge_counts = {}
    for concepts in grouped:
        for c1, c2 in combinations(sorted(set(concepts)), 2):
            edge_counts[(c1, c2)] = edge_counts.get((c1, c2), 0) + 1

    G = nx.Graph()
    for (c1, c2), weight in edge_counts.items():
        if weight >= max(MIN_CONCEPT_COOC, 1):
            G.add_edge(c1, c2, weight=weight)

    G = apply_degree_filter(G, MIN_DEGREE)
    suffix = f"c{MIN_CONCEPT_COOC}_d{MIN_DEGREE}"
    save_graph(G, "concept_cooccurrence", suffix)


def create_field_sharing_graph():
    print("Creating Research Field Sharing graph...")
    edges_file = os.path.join(DATA_DIR, "openalex_field_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    df = pd.read_csv(edges_file)
    grouped = df.groupby('paper_id')['field_name'].apply(list)

    edge_counts = {}
    for fields in grouped:
        for f1, f2 in combinations(sorted(set(fields)), 2):
            edge_counts[(f1, f2)] = edge_counts.get((f1, f2), 0) + 1

    G = nx.Graph()
    for (f1, f2), weight in edge_counts.items():
        if weight >= max(MIN_FIELD_COOC, 1):
            G.add_edge(f1, f2, weight=weight)

    G = apply_degree_filter(G, MIN_DEGREE)
    suffix = f"f{MIN_FIELD_COOC}_d{MIN_DEGREE}"
    save_graph(G, "field_sharing", suffix)


if __name__ == "__main__":
    create_coauthorship_graph()
    create_bibliographic_coupling_graph()
    create_concept_cooccurrence_graph()
    create_field_sharing_graph()
    print("All OpenAlex graphs created and saved to nx_graphs/.")
