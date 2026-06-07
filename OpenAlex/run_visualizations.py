"""
run_visualizations.py — OpenAlex
Visualises all 8 graphs with degree thresholds targeting ~130 nodes.
Run from the OpenAlex/ folder:
    python run_visualizations.py
"""

from visualize_biblio_graphs import visualize_graph

# Normalized graphs only — raw graphs excluded (too dense for browser visualization)
JOBS = [
    ("field_sharing_norm_f0_d0.pkl",                 0),
    ("coauthorship_norm_w0_d0.pkl",              19.4639),
    ("bibliographic_coupling_norm_r0_d0.pkl",   154.8608),
    ("concept_cooccurrence_norm_c0_d0.pkl",        4.0),
]

if __name__ == "__main__":
    for filename, min_deg in JOBS:
        print(f"\n>>> {filename}  (min_degree={min_deg})")
        visualize_graph(filename, min_degree=min_deg)
    print("\nAll visualizations complete. HTMLs saved to pyvis_graphs/.")
