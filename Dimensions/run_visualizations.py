"""
run_visualizations.py — Dimensions
Runs all visualize_biblio_graphs.py commands with the appropriate --min_degree
thresholds to produce graphs of ~130 nodes for comfortable PyVis interaction.

Run from the Dimensions/ folder:
    python run_visualizations.py
"""

import subprocess
import sys

COMMANDS = [
    # field_sharing: 70 nodes — plot as-is
    ["python", "visualize_biblio_graphs.py", "field_sharing_f0_d0.pkl"],
    ["python", "visualize_biblio_graphs.py", "field_sharing_norm_f0_d0.pkl"],

    # co-authorship
    ["python", "visualize_biblio_graphs.py", "coauthorship_norm_w0_d0.pkl", "--min_degree", "22"],
    ["python", "visualize_biblio_graphs.py", "coauthorship_w0_d0.pkl",      "--min_degree", "3011"],

    # bibliographic coupling
    ["python", "visualize_biblio_graphs.py", "bibliographic_coupling_norm_r0_d0.pkl", "--min_degree", "139.72"],
    ["python", "visualize_biblio_graphs.py", "bibliographic_coupling_r0_d0.pkl",      "--min_degree", "7489"],

    # concept co-occurrence
    ["python", "visualize_biblio_graphs.py", "concept_cooccurrence_norm_c0_d0.pkl", "--min_degree", "730.25"],
    ["python", "visualize_biblio_graphs.py", "concept_cooccurrence_c0_d0.pkl",      "--min_degree", "167731"],
]

if __name__ == "__main__":
    for cmd in COMMANDS:
        print(f"\n>>> {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"  ERROR: command failed with return code {result.returncode}", file=sys.stderr)
    print("\nAll visualizations complete. HTMLs saved to pyvis_graphs/.")
