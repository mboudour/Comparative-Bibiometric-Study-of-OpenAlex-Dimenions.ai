import os
import pandas as pd
import networkx as nx
import pickle
import math
from itertools import combinations

DATA_DIR = "data"
GRAPH_DIR = "nx_graphs"
os.makedirs(GRAPH_DIR, exist_ok=True)

# =============================================================================
# EXTRACTION MODE AND PARAMETERS
# =============================================================================
# Two extraction modes are available:
#   "threshold" : Uses absolute edge weight and node degree cuts (legacy)
#   "ps_core"   : Uses Ps-core decomposition based on weighted degree (recommended)
EXTRACTION_MODE = "ps_core"  # Options: "threshold", "ps_core"

# Parameters for "threshold" mode:
MIN_COAUTH_WEIGHT = 0
MIN_SHARED_REFS   = 0
MIN_CONCEPT_COOC  = 0
MIN_FIELD_COOC    = 0
MIN_DEGREE        = 0

# Parameters for "ps_core" mode:
# t is the minimum weighted degree (strength of internal collaboration)
PS_CORE_T_COAUTH = 1.0
PS_CORE_T_BIB    = 0.5
PS_CORE_T_CONCEPT= 1.0
PS_CORE_T_FIELD  = 1.0

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def apply_degree_filter(G, min_degree):
    if min_degree > 0:
        nodes_to_keep = [n for n, d in G.degree() if d >= min_degree]
        G = G.subgraph(nodes_to_keep).copy()
    return G

def extract_ps_core(G, t):
    """
    Extracts the Ps-core at level t from a weighted graph G.
    The Ps-core is the maximal subgraph where every node has a weighted degree >= t.
    """
    core = G.copy()
    while True:
        # Calculate weighted degree for all nodes in current core
        wdeg = {n: sum(d.get('weight', 1.0) for _, _, d in core.edges(n, data=True)) 
                for n in core.nodes()}
        
        # Find nodes below threshold
        to_remove = [n for n, w in wdeg.items() if w < t]
        
        if not to_remove:
            break  # All remaining nodes meet the threshold
            
        core.remove_nodes_from(to_remove)
        
    return core

def save_graph(G, base_name, suffix):
    filename = f"{base_name}_{suffix}.pkl"
    path = os.path.join(GRAPH_DIR, filename)
    with open(path, "wb") as f:
        pickle.dump(G, f)
    print(f"  Saved: {filename}  (Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()})")

# =============================================================================
# GRAPH CREATION WITH NORMALIZATIONS
# =============================================================================

def create_coauthorship_graph():
    print("Creating Co-authorship graph (Strict Fractional Normalization)...")
    edges_file = os.path.join(DATA_DIR, "dimensions_coauth_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found. Run fetch_data.py first.")
        return

    df = pd.read_csv(edges_file)
    
    # Calculate paper degree (number of authors per paper)
    authors_per_paper = pd.concat([
        df[['paper_id', 'source']].rename(columns={'source': 'author'}),
        df[['paper_id', 'target']].rename(columns={'target': 'author'})
    ]).drop_duplicates()
    
    paper_degree = authors_per_paper.groupby('paper_id').size().to_dict()
    
    # Apply strict fractional normalization: weight = 1 / max(1, k-1)
    df['k'] = df['paper_id'].map(paper_degree)
    df['norm_weight'] = 1.0 / df['k'].apply(lambda x: max(1, x - 1))
    
    # Aggregate normalized weights
    edge_weights = df.groupby(['source', 'target'])['norm_weight'].sum().reset_index(name='weight')

    G = nx.Graph()
    for _, row in edge_weights.iterrows():
        G.add_edge(row['source'], row['target'], weight=row['weight'])

    if EXTRACTION_MODE == "threshold":
        if MIN_COAUTH_WEIGHT > 0:
            edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < MIN_COAUTH_WEIGHT]
            G.remove_edges_from(edges_to_remove)
            G.remove_nodes_from(list(nx.isolates(G)))
        G = apply_degree_filter(G, MIN_DEGREE)
        suffix = f"norm_w{MIN_COAUTH_WEIGHT}_d{MIN_DEGREE}"
    else:
        G = extract_ps_core(G, PS_CORE_T_COAUTH)
        suffix = f"norm_ps{PS_CORE_T_COAUTH}"
        
    save_graph(G, "coauthorship", suffix)


def create_bibliographic_coupling_graph():
    print("Creating Bibliographic Coupling graph (Cosine Normalization)...")
    edges_file = os.path.join(DATA_DIR, "dimensions_bib_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    df = pd.read_csv(edges_file)
    
    # Calculate reference list length for each paper
    ref_counts = df.groupby('paper_id').size().to_dict()
    
    # Create bipartite graph
    B = nx.Graph()
    papers = df['paper_id'].unique()
    refs = df['reference_id'].unique()
    B.add_nodes_from(papers, bipartite=0)
    B.add_nodes_from(refs, bipartite=1)
    B.add_edges_from(zip(df['paper_id'], df['reference_id']))

    # Project to papers, calculating raw shared references
    G_raw = nx.bipartite.weighted_projected_graph(B, papers)
    
    # Apply cosine normalization: |R_i ∩ R_j| / sqrt(|R_i| * |R_j|)
    G = nx.Graph()
    for u, v, data in G_raw.edges(data=True):
        raw_weight = data['weight']
        norm_weight = raw_weight / math.sqrt(ref_counts[u] * ref_counts[v])
        G.add_edge(u, v, weight=norm_weight)

    if EXTRACTION_MODE == "threshold":
        if MIN_SHARED_REFS > 0:
            edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < MIN_SHARED_REFS]
            G.remove_edges_from(edges_to_remove)
            G.remove_nodes_from(list(nx.isolates(G)))
        G = apply_degree_filter(G, MIN_DEGREE)
        suffix = f"norm_r{MIN_SHARED_REFS}_d{MIN_DEGREE}"
    else:
        G = extract_ps_core(G, PS_CORE_T_BIB)
        suffix = f"norm_ps{PS_CORE_T_BIB}"
        
    save_graph(G, "bibliographic_coupling", suffix)


def create_concept_cooccurrence_graph():
    print("Creating Concept Co-occurrence graph (Cosine Normalization)...")
    edges_file = os.path.join(DATA_DIR, "dimensions_concept_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    df = pd.read_csv(edges_file)
    
    # Calculate concept frequency
    concept_freq = df.groupby('concept_name')['paper_id'].nunique().to_dict()
    
    grouped = df.groupby('paper_id')['concept_name'].apply(list)

    edge_counts = {}
    for concepts in grouped:
        for c1, c2 in combinations(sorted(set(concepts)), 2):
            edge_counts[(c1, c2)] = edge_counts.get((c1, c2), 0) + 1

    G = nx.Graph()
    for (c1, c2), raw_weight in edge_counts.items():
        # Cosine normalization
        norm_weight = raw_weight / math.sqrt(concept_freq[c1] * concept_freq[c2])
        G.add_edge(c1, c2, weight=norm_weight)

    if EXTRACTION_MODE == "threshold":
        if MIN_CONCEPT_COOC > 0:
            edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < MIN_CONCEPT_COOC]
            G.remove_edges_from(edges_to_remove)
            G.remove_nodes_from(list(nx.isolates(G)))
        G = apply_degree_filter(G, MIN_DEGREE)
        suffix = f"norm_c{MIN_CONCEPT_COOC}_d{MIN_DEGREE}"
    else:
        G = extract_ps_core(G, PS_CORE_T_CONCEPT)
        suffix = f"norm_ps{PS_CORE_T_CONCEPT}"
        
    save_graph(G, "concept_cooccurrence", suffix)


def create_field_sharing_graph():
    print("Creating Research Field Sharing graph (Cosine Normalization)...")
    edges_file = os.path.join(DATA_DIR, "dimensions_field_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    df = pd.read_csv(edges_file)
    
    # Calculate field frequency
    field_freq = df.groupby('field_name')['paper_id'].nunique().to_dict()
    
    grouped = df.groupby('paper_id')['field_name'].apply(list)

    edge_counts = {}
    for fields in grouped:
        for f1, f2 in combinations(sorted(set(fields)), 2):
            edge_counts[(f1, f2)] = edge_counts.get((f1, f2), 0) + 1

    G = nx.Graph()
    for (f1, f2), raw_weight in edge_counts.items():
        # Cosine normalization
        norm_weight = raw_weight / math.sqrt(field_freq[f1] * field_freq[f2])
        G.add_edge(f1, f2, weight=norm_weight)

    if EXTRACTION_MODE == "threshold":
        if MIN_FIELD_COOC > 0:
            edges_to_remove = [(u, v) for u, v, d in G.edges(data=True) if d['weight'] < MIN_FIELD_COOC]
            G.remove_edges_from(edges_to_remove)
            G.remove_nodes_from(list(nx.isolates(G)))
        G = apply_degree_filter(G, MIN_DEGREE)
        suffix = f"norm_f{MIN_FIELD_COOC}_d{MIN_DEGREE}"
    else:
        G = extract_ps_core(G, PS_CORE_T_FIELD)
        suffix = f"norm_ps{PS_CORE_T_FIELD}"
        
    save_graph(G, "field_sharing", suffix)


if __name__ == "__main__":
    create_coauthorship_graph()
    create_bibliographic_coupling_graph()
    create_concept_cooccurrence_graph()
    create_field_sharing_graph()
    print(f"All Dimensions graphs created using {EXTRACTION_MODE} mode and saved to nx_graphs/.")
