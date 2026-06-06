# Comparison Scripts

These scripts implement the four-level network comparison methodology described in the main README. Run all scripts from the **project root** (one level above this folder).

## Prerequisites

```bash
pip install pandas networkx scipy scikit-learn python-louvain matplotlib
```

## Scripts

| Script | Level | Output |
|---|---|---|
| `compare_coverage.py` | 1 — Coverage | `coverage_results.csv` |
| `compare_structure.py` | 2 — Structure | `structure_results.csv`, `figures/*.png` |
| `compare_centrality.py` | 2 — Structure | `centrality_results.csv` |
| `compare_communities.py` | 3 — Inference | `community_results.csv` |
| `compare_qap.py` | 4 — QAP | `qap_results.csv` |

## Usage

```bash
python comparison/compare_coverage.py
python comparison/compare_structure.py
python comparison/compare_centrality.py
python comparison/compare_communities.py
python comparison/compare_qap.py
```

Each script reads the full untruncated `.pkl` graphs from `OpenAlex/nx_graphs/` and `Dimensions/nx_graphs/` and writes its results to this folder. All scripts align nodes by label (string identifier) — ORCID for authors, DOI for papers, concept/field labels for the remaining network types.

**Note on QAP**: For very large graphs (> 10,000 shared nodes), `compare_qap.py` will skip the graph and report `nan`. Run the comparison on degree-threshold or Ps-core truncated graphs in that case by pointing the script at the truncated `.pkl` files.
