"""
run_visualizations.py — OpenAlex
Runs all visualize_biblio_graphs.py commands with the appropriate --min_degree
thresholds to produce graphs of ~130 nodes for comfortable PyVis interaction.

Run from the OpenAlex/ folder:
    python run_visualizations.py
"""

import subprocess
import sys

COMMANDS = [
    # field_sharing: 26 nodes — plot as-is
    ["python", "visualize_biblio_graphs.py", "field_sharing_f0_d0.pkl"],
    ["python", "visualize_biblio_graphs.py", "field_sharing_norm_f0_d0.pkl"],

    # co-authorship — --min_degree placed before filename for correct argparse parsing
    ["python", "visualize_biblio_graphs.py", "--min_degree", "19.46", "coauthorship_norm_w0_d0.pkl"],
    ["python", "visualize_biblio_graphs.py", "--min_degree", "206",   "coauthorship_w0_d0.pkl"],

    # bibliographic coupling
    ["python", "visualize_biblio_graphs.py", "--min_degree", "154.86", "bibliographic_coupling_norm_r0_d0.pkl"],
    ["python", "visualize_biblio_graphs.py", "--min_degree", "7418",   "bibliographic_coupling_r0_d0.pkl"],

    # concept co-occurrence
    ["python", "visualize_biblio_graphs.py", "--min_degree", "4.0", "concept_cooccurrence_norm_c0_d0.pkl"],
    ["python", "visualize_biblio_graphs.py", "--min_degree", "222", "concept_cooccurrence_c0_d0.pkl"],
]

if __name__ == "__main__":
    for cmd in COMMANDS:
        print(f"\n>>> {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"  ERROR: command failed with return code {result.returncode}", file=sys.stderr)
    print("\nAll visualizations complete. HTMLs saved to pyvis_graphs/.")
