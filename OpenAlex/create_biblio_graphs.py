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
#   "threshold" : Uses absolute edge weight and node degree cuts
#   "ps_core"   : Uses Ps-core decomposition based on weighted degree
EXTRACTION_MODE = "threshold"  # Options: "threshold", "ps_core"

# Parameters for "threshold" mode (0 = no truncation):
MIN_COAUTH_WEIGHT = 0
MIN_SHARED_REFS   = 0
MIN_CONCEPT_COOC  = 0
MIN_FIELD_COOC    = 0
MIN_DEGREE        = 0

# Parameters for "ps_core" mode:
PS_CORE_T_COAUTH  = 1.0
PS_CORE_T_BIB     = 0.5
PS_CORE_T_CONCEPT = 1.0
PS_CORE_T_FIELD   = 1.0

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def graph_exists(filename):
    """Return True if the graph pkl already exists (caching check)."""
    path = os.path.join(GRAPH_DIR, filename)
    if os.path.exists(path):
        print(f"  Cached — skipping: {filename}")
        return True
    return False

def apply_degree_filter(G, min_degree):
    if min_degree > 0:
        nodes_to_keep = [n for n, d in G.degree() if d >= min_degree]
        G = G.subgraph(nodes_to_keep).copy()
    return G

def extract_ps_core(G, t):
    """Extracts the Ps-core at level t: maximal subgraph where every node
    has weighted degree >= t."""
    core = G.copy()
    while True:
        wdeg = {n: sum(d.get('weight', 1.0) for _, _, d in core.edges(n, data=True))
                for n in core.nodes()}
        to_remove = [n for n, w in wdeg.items() if w < t]
        if not to_remove:
            break
        core.remove_nodes_from(to_remove)
    return core

def save_graph(G, filename):
    path = os.path.join(GRAPH_DIR, filename)
    with open(path, "wb") as f:
        pickle.dump(G, f)
    print(f"  Saved: {filename}  (Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()})")

def apply_extraction(G, mode, raw_param, raw_val, degree_val,
                     ps_t, raw_suffix, norm_suffix=None):
    """Apply threshold or ps_core extraction and return (G, suffix)."""
    if mode == "threshold":
        if raw_val > 0:
            edges_to_remove = [(u, v) for u, v, d in G.edges(data=True)
                               if d['weight'] < raw_val]
            G.remove_edges_from(edges_to_remove)
            G.remove_nodes_from(list(nx.isolates(G)))
        G = apply_degree_filter(G, degree_val)
        suffix = raw_suffix
    else:
        G = extract_ps_core(G, ps_t)
        suffix = norm_suffix
    return G, suffix

# =============================================================================
# GRAPH CREATION — each function saves BOTH raw and normalized graphs
# =============================================================================

def create_coauthorship_graph():
    print("Creating Co-authorship graphs...")
    edges_file = os.path.join(DATA_DIR, "openalex_coauth_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found. Run fetch_data.py first.")
        return

    # Determine output filenames
    if EXTRACTION_MODE == "threshold":
        raw_fname  = f"coauthorship_w{MIN_COAUTH_WEIGHT}_d{MIN_DEGREE}.pkl"
        norm_fname = f"coauthorship_norm_w{MIN_COAUTH_WEIGHT}_d{MIN_DEGREE}.pkl"
    else:
        raw_fname  = f"coauthorship_ps{PS_CORE_T_COAUTH}.pkl"
        norm_fname = f"coauthorship_norm_ps{PS_CORE_T_COAUTH}.pkl"

    raw_needed  = not graph_exists(raw_fname)
    norm_needed = not graph_exists(norm_fname)
    if not raw_needed and not norm_needed:
        return

    df = pd.read_csv(edges_file)

    # --- RAW graph (unweighted co-authorship count) ---
    if raw_needed:
        print("  Building raw co-authorship graph...")
        raw_edge_weights = df.groupby(['source', 'target']).size().reset_index(name='weight')
        G_raw = nx.Graph()
        for _, row in raw_edge_weights.iterrows():
            G_raw.add_edge(row['source'], row['target'], weight=row['weight'])
        if EXTRACTION_MODE == "threshold":
            if MIN_COAUTH_WEIGHT > 0:
                G_raw.remove_edges_from([(u, v) for u, v, d in G_raw.edges(data=True)
                                         if d['weight'] < MIN_COAUTH_WEIGHT])
                G_raw.remove_nodes_from(list(nx.isolates(G_raw)))
            G_raw = apply_degree_filter(G_raw, MIN_DEGREE)
        else:
            G_raw = extract_ps_core(G_raw, PS_CORE_T_COAUTH)
        save_graph(G_raw, raw_fname)

    # --- NORMALIZED graph (strict fractional normalization) ---
    if norm_needed:
        print("  Building normalized co-authorship graph (strict fractional)...")
        authors_per_paper = pd.concat([
            df[['paper_id', 'source']].rename(columns={'source': 'author'}),
            df[['paper_id', 'target']].rename(columns={'target': 'author'})
        ]).drop_duplicates()
        paper_degree = authors_per_paper.groupby('paper_id').size().to_dict()
        df['k'] = df['paper_id'].map(paper_degree)
        df['norm_weight'] = 1.0 / df['k'].apply(lambda x: max(1, x - 1))
        edge_weights = df.groupby(['source', 'target'])['norm_weight'].sum().reset_index(name='weight')
        G_norm = nx.Graph()
        for _, row in edge_weights.iterrows():
            G_norm.add_edge(row['source'], row['target'], weight=row['weight'])
        if EXTRACTION_MODE == "threshold":
            if MIN_COAUTH_WEIGHT > 0:
                G_norm.remove_edges_from([(u, v) for u, v, d in G_norm.edges(data=True)
                                          if d['weight'] < MIN_COAUTH_WEIGHT])
                G_norm.remove_nodes_from(list(nx.isolates(G_norm)))
            G_norm = apply_degree_filter(G_norm, MIN_DEGREE)
        else:
            G_norm = extract_ps_core(G_norm, PS_CORE_T_COAUTH)
        save_graph(G_norm, norm_fname)


def create_bibliographic_coupling_graph():
    print("Creating Bibliographic Coupling graphs...")
    edges_file = os.path.join(DATA_DIR, "openalex_bib_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    if EXTRACTION_MODE == "threshold":
        raw_fname  = f"bibliographic_coupling_r{MIN_SHARED_REFS}_d{MIN_DEGREE}.pkl"
        norm_fname = f"bibliographic_coupling_norm_r{MIN_SHARED_REFS}_d{MIN_DEGREE}.pkl"
    else:
        raw_fname  = f"bibliographic_coupling_ps{PS_CORE_T_BIB}.pkl"
        norm_fname = f"bibliographic_coupling_norm_ps{PS_CORE_T_BIB}.pkl"

    raw_needed  = not graph_exists(raw_fname)
    norm_needed = not graph_exists(norm_fname)
    if not raw_needed and not norm_needed:
        return

    df = pd.read_csv(edges_file)
    ref_counts = df.groupby('paper_id').size().to_dict()

    B = nx.Graph()
    papers = df['paper_id'].unique()
    refs   = df['reference_id'].unique()
    B.add_nodes_from(papers, bipartite=0)
    B.add_nodes_from(refs,   bipartite=1)
    B.add_edges_from(zip(df['paper_id'], df['reference_id']))
    G_proj = nx.bipartite.weighted_projected_graph(B, papers)

    # --- RAW graph ---
    if raw_needed:
        print("  Building raw bibliographic coupling graph...")
        G_raw = nx.Graph()
        for u, v, data in G_proj.edges(data=True):
            if ref_counts.get(u) and ref_counts.get(v):
                G_raw.add_edge(u, v, weight=data['weight'])
        if EXTRACTION_MODE == "threshold":
            if MIN_SHARED_REFS > 0:
                G_raw.remove_edges_from([(u, v) for u, v, d in G_raw.edges(data=True)
                                         if d['weight'] < MIN_SHARED_REFS])
                G_raw.remove_nodes_from(list(nx.isolates(G_raw)))
            G_raw = apply_degree_filter(G_raw, MIN_DEGREE)
        else:
            G_raw = extract_ps_core(G_raw, PS_CORE_T_BIB)
        save_graph(G_raw, raw_fname)

    # --- NORMALIZED graph (cosine) ---
    if norm_needed:
        print("  Building normalized bibliographic coupling graph (cosine)...")
        G_norm = nx.Graph()
        for u, v, data in G_proj.edges(data=True):
            rc_u = ref_counts.get(u)
            rc_v = ref_counts.get(v)
            if rc_u and rc_v:
                norm_weight = data['weight'] / math.sqrt(rc_u * rc_v)
                G_norm.add_edge(u, v, weight=norm_weight)
        if EXTRACTION_MODE == "threshold":
            if MIN_SHARED_REFS > 0:
                G_norm.remove_edges_from([(u, v) for u, v, d in G_norm.edges(data=True)
                                          if d['weight'] < MIN_SHARED_REFS])
                G_norm.remove_nodes_from(list(nx.isolates(G_norm)))
            G_norm = apply_degree_filter(G_norm, MIN_DEGREE)
        else:
            G_norm = extract_ps_core(G_norm, PS_CORE_T_BIB)
        save_graph(G_norm, norm_fname)


def create_concept_cooccurrence_graph():
    print("Creating Concept Co-occurrence graphs...")
    edges_file = os.path.join(DATA_DIR, "openalex_concept_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    if EXTRACTION_MODE == "threshold":
        raw_fname  = f"concept_cooccurrence_c{MIN_CONCEPT_COOC}_d{MIN_DEGREE}.pkl"
        norm_fname = f"concept_cooccurrence_norm_c{MIN_CONCEPT_COOC}_d{MIN_DEGREE}.pkl"
    else:
        raw_fname  = f"concept_cooccurrence_ps{PS_CORE_T_CONCEPT}.pkl"
        norm_fname = f"concept_cooccurrence_norm_ps{PS_CORE_T_CONCEPT}.pkl"

    raw_needed  = not graph_exists(raw_fname)
    norm_needed = not graph_exists(norm_fname)
    if not raw_needed and not norm_needed:
        return

    df = pd.read_csv(edges_file)
    concept_freq = df.groupby('concept_name')['paper_id'].nunique().to_dict()
    grouped = df.groupby('paper_id')['concept_name'].apply(list)

    raw_edge_counts  = {}
    norm_edge_counts = {}
    for concepts in grouped:
        clean = [c for c in concepts if isinstance(c, str) and c]
        for c1, c2 in combinations(sorted(set(clean)), 2):
            raw_edge_counts[(c1, c2)]  = raw_edge_counts.get((c1, c2), 0) + 1
            norm_edge_counts[(c1, c2)] = norm_edge_counts.get((c1, c2), 0) + 1

    # --- RAW graph ---
    if raw_needed:
        print("  Building raw concept co-occurrence graph...")
        G_raw = nx.Graph()
        for (c1, c2), w in raw_edge_counts.items():
            G_raw.add_edge(c1, c2, weight=w)
        if EXTRACTION_MODE == "threshold":
            if MIN_CONCEPT_COOC > 0:
                G_raw.remove_edges_from([(u, v) for u, v, d in G_raw.edges(data=True)
                                         if d['weight'] < MIN_CONCEPT_COOC])
                G_raw.remove_nodes_from(list(nx.isolates(G_raw)))
            G_raw = apply_degree_filter(G_raw, MIN_DEGREE)
        else:
            G_raw = extract_ps_core(G_raw, PS_CORE_T_CONCEPT)
        save_graph(G_raw, raw_fname)

    # --- NORMALIZED graph (cosine) ---
    if norm_needed:
        print("  Building normalized concept co-occurrence graph (cosine)...")
        G_norm = nx.Graph()
        for (c1, c2), raw_w in norm_edge_counts.items():
            norm_weight = raw_w / math.sqrt(concept_freq[c1] * concept_freq[c2])
            G_norm.add_edge(c1, c2, weight=norm_weight)
        if EXTRACTION_MODE == "threshold":
            if MIN_CONCEPT_COOC > 0:
                G_norm.remove_edges_from([(u, v) for u, v, d in G_norm.edges(data=True)
                                          if d['weight'] < MIN_CONCEPT_COOC])
                G_norm.remove_nodes_from(list(nx.isolates(G_norm)))
            G_norm = apply_degree_filter(G_norm, MIN_DEGREE)
        else:
            G_norm = extract_ps_core(G_norm, PS_CORE_T_CONCEPT)
        save_graph(G_norm, norm_fname)


def create_field_sharing_graph():
    print("Creating Research Field Sharing graphs...")
    edges_file = os.path.join(DATA_DIR, "openalex_field_edges.csv")
    if not os.path.exists(edges_file):
        print(f"  {edges_file} not found.")
        return

    if EXTRACTION_MODE == "threshold":
        raw_fname  = f"field_sharing_f{MIN_FIELD_COOC}_d{MIN_DEGREE}.pkl"
        norm_fname = f"field_sharing_norm_f{MIN_FIELD_COOC}_d{MIN_DEGREE}.pkl"
    else:
        raw_fname  = f"field_sharing_ps{PS_CORE_T_FIELD}.pkl"
        norm_fname = f"field_sharing_norm_ps{PS_CORE_T_FIELD}.pkl"

    raw_needed  = not graph_exists(raw_fname)
    norm_needed = not graph_exists(norm_fname)
    if not raw_needed and not norm_needed:
        return

    df = pd.read_csv(edges_file)
    field_freq = df.groupby('field_name')['paper_id'].nunique().to_dict()
    grouped = df.groupby('paper_id')['field_name'].apply(list)

    raw_edge_counts  = {}
    norm_edge_counts = {}
    for fields in grouped:
        clean = [f for f in fields if isinstance(f, str) and f]
        for f1, f2 in combinations(sorted(set(clean)), 2):
            raw_edge_counts[(f1, f2)]  = raw_edge_counts.get((f1, f2), 0) + 1
            norm_edge_counts[(f1, f2)] = norm_edge_counts.get((f1, f2), 0) + 1

    # --- RAW graph ---
    if raw_needed:
        print("  Building raw field sharing graph...")
        G_raw = nx.Graph()
        for (f1, f2), w in raw_edge_counts.items():
            G_raw.add_edge(f1, f2, weight=w)
        if EXTRACTION_MODE == "threshold":
            if MIN_FIELD_COOC > 0:
                G_raw.remove_edges_from([(u, v) for u, v, d in G_raw.edges(data=True)
                                         if d['weight'] < MIN_FIELD_COOC])
                G_raw.remove_nodes_from(list(nx.isolates(G_raw)))
            G_raw = apply_degree_filter(G_raw, MIN_DEGREE)
        else:
            G_raw = extract_ps_core(G_raw, PS_CORE_T_FIELD)
        save_graph(G_raw, raw_fname)

    # --- NORMALIZED graph (cosine) ---
    if norm_needed:
        print("  Building normalized field sharing graph (cosine)...")
        G_norm = nx.Graph()
        for (f1, f2), raw_w in norm_edge_counts.items():
            norm_weight = raw_w / math.sqrt(field_freq[f1] * field_freq[f2])
            G_norm.add_edge(f1, f2, weight=norm_weight)
        if EXTRACTION_MODE == "threshold":
            if MIN_FIELD_COOC > 0:
                G_norm.remove_edges_from([(u, v) for u, v, d in G_norm.edges(data=True)
                                          if d['weight'] < MIN_FIELD_COOC])
                G_norm.remove_nodes_from(list(nx.isolates(G_norm)))
            G_norm = apply_degree_filter(G_norm, MIN_DEGREE)
        else:
            G_norm = extract_ps_core(G_norm, PS_CORE_T_FIELD)
        save_graph(G_norm, norm_fname)


if __name__ == "__main__":
    create_coauthorship_graph()
    create_bibliographic_coupling_graph()
    create_concept_cooccurrence_graph()
    create_field_sharing_graph()
    print(f"\nAll OpenAlex graphs processed using '{EXTRACTION_MODE}' mode. Saved to nx_graphs/.")
