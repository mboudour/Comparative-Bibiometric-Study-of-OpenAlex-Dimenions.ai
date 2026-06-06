# Comparative Bibliometric Study: OpenAlex & Dimensions.ai

A reproducible data collection and network analysis pipeline for comparing scientometric networks derived from the **OpenAlex** (open) and **Dimensions.ai** (proprietary) bibliographic databases.

This project supports the study:

> *"Do Open and Proprietary Bibliographic Databases Produce Equivalent Scientometric Networks? A Comparative Study of OpenAlex and Dimensions.ai"*

---

## Journal Corpus

20 journals across three thematic clusters, covering the period **2010–2024** (~45,000–50,000 articles). The full list is maintained in the shared `journals.csv` at the project root.

| Journal | ISSN | Electronic ISSN | OpenAlex ID | Cluster |
|---|---|---|---|---|
| Scientometrics | 0138-9130 | 1588-2861 | S148561398 | Scientometrics & Informetrics |
| Journal of Informetrics | 1751-1577 | 1875-5879 | S205292342 | Scientometrics & Informetrics |
| Quantitative Science Studies | 2641-3337 | 2641-3337 | S4210195326 | Scientometrics & Informetrics |
| Research Evaluation | 0958-2029 | 1471-5449 | S16793705 | Scientometrics & Informetrics |
| JASIST | 2330-1635 | 2330-1643 | S4210197613 | Scientometrics & Informetrics |
| Social Science Computer Review | 0894-4393 | 1552-8286 | S127118166 | Scientometrics & Informetrics |
| Research Policy | 0048-7333 | 1873-7625 | S9731383 | Scientometrics & Informetrics |
| Information Processing & Management | 0306-4573 | 1873-5371 | S174847851 | Information Science |
| Journal of Information Science | 0165-5515 | 1741-6485 | S68913162 | Information Science |
| Aslib Journal of Information Management | 2050-3806 | 2050-3806 | S4210181081 | Information Science |
| Library & Information Science Research | 0740-8188 | 1879-1034 | S186163925 | Information Science |
| Online Information Review | 1468-4527 | 1468-4527 | S931548824 | Information Science |
| Journal of Documentation | 0022-0418 | 1758-7379 | S10082577 | Information Science |
| The Lancet Digital Health | 2589-7500 | 2589-7500 | S4210237014 | AI in Health / Medicine |
| npj Digital Medicine | 2398-6352 | 2398-6352 | S4210195431 | AI in Health / Medicine |
| Artificial Intelligence in Medicine | 0933-3657 | 1873-2860 | S42468263 | AI in Health / Medicine |
| JAMIA | 1527-974X | 1527-974X | S129839026 | AI in Health / Medicine |
| Journal of Medical Internet Research | 1438-8871 | 1438-8871 | S17147534 | AI in Health / Medicine |
| Journal of Biomedical Informatics | 1532-0464 | 1532-0480 | S11622463 | AI in Health / Medicine |
| Digital Health | 2055-2076 | 2055-2076 | S4210188408 | AI in Health / Medicine |

---

## Four Scientometric Networks and Normalization

Each pipeline produces four network types. Because raw counts can be heavily biased by paper size (e.g., medical papers often have many more authors and references than scientometrics papers) or hub entities (e.g., highly frequent concepts), **fractional or cosine normalization is applied during graph creation**.

| Network | Node Type | Edge Criterion | Normalization |
|---|---|---|---|
| **Co-authorship** | Author | Co-authored at least one paper | **Strict Fractional** (weight += 1/max(1, k−1) per paper, where k = number of authors) |
| **Bibliographic Coupling** | Paper | Cite at least one common reference | **Cosine** (normalized by reference list lengths) |
| **Concept Co-occurrence** | Concept / Keyword | Appear together in at least one paper | **Cosine** (normalized by concept frequencies) |
| **Research Field Sharing** | Field / FOR Category | Co-assigned to at least one paper | **Cosine** (normalized by field frequencies) |

---

## Prerequisites

```bash
pip install requests pandas networkx pyvis
```

---

## Setup

### OpenAlex

OpenAlex does not require an API key for basic access, but providing one unlocks higher rate limits. A contact email is used separately to access the **polite pool**.

Edit `OpenAlex/key.txt`:
```
your_email@example.com
YOUR_OPENALEX_API_KEY_HERE
```
- **Line 1:** your contact email (required for polite pool)
- **Line 2:** your OpenAlex API key (optional)

To request an OpenAlex API key visit: [https://openalex.org/](https://openalex.org/)

### Dimensions.ai

A Dimensions API key is required. Edit `Dimensions/key.txt`:
```
YOUR_DIMENSIONS_API_KEY_HERE
```
To obtain a key visit: [https://www.dimensions.ai/](https://www.dimensions.ai/)

---

## Pipeline

Run the scripts in sequence from within each subfolder. **Always `cd` into the subfolder first**, as all paths are relative.

```bash
cd OpenAlex
python fetch_data.py
python create_biblio_graphs.py
python find_thresholds.py          # optional: find degree thresholds for ~130 nodes
python find_pscore_thresholds.py   # optional: find Ps-core thresholds for ~130 nodes
python run_visualizations.py       # degree-threshold visualizations
python run_pscore_visualizations.py  # Ps-core visualizations
```

Repeat identically from the `Dimensions/` folder.

---

## Step 1 — Data Fetching (`fetch_data.py`)

Fetches all articles from the 20 target journals within the 2010–2024 window. Both scripts read the shared `../journals.csv` at the project root.

**OpenAlex:** Uses cursor-based pagination (200 records per page) against the `/works` endpoint, filtering by `primary_location.source.id`, `publication_year`, and `type:article`. Fields fetched: `id`, `doi`, `title`, `publication_year`, `primary_location`, `authorships`, `referenced_works`, `concepts`, `topics`.

**Dimensions:** Authenticates via `POST /api/auth.json` to obtain a JWT token, then issues DSL queries using `limit`/`skip` pagination, filtering by ISSN list, year range, and `type = "article"`. Fields fetched: `id`, `doi`, `title`, `year`, `journal`, `authors`, `researchers`, `reference_ids`, `concepts`, `concepts_scores`, `category_for`, `open_access`, `times_cited`, `field_citation_ratio`.

**Outputs to `data/`:**

| File | Contents |
|---|---|
| `openalex_raw.pkl` / `dimensions_raw.pkl` | Pickled `pd.DataFrame` — one row per article, all fetched fields preserved |
| `*_nodes.csv` | Flat article catalog (id, doi, title, year, journal) |
| `*_coauth_edges.csv` | Author–author pairs per paper |
| `*_bib_edges.csv` | Paper–reference pairs |
| `*_concept_edges.csv` | Paper–concept pairs |
| `*_field_edges.csv` | Paper–field pairs |

---

## Step 2 — Graph Construction (`create_biblio_graphs.py`)

Reads the CSV edge lists and constructs four normalized NetworkX graphs, serialised as pickle files in `nx_graphs/`.

The script offers two **extraction modes** controlled by the `EXTRACTION_MODE` variable at the top of the file.

### Mode 1: Ps-core Extraction (`EXTRACTION_MODE = "ps_core"`) — Recommended

Extracts the maximal subgraph where every node's weighted degree is at least *t*. This is a principled, scale-invariant, data-driven approach that identifies the productive backbone of the network, following the Batagelj-Zaveršnik O(m) peeling algorithm.

| Parameter | Applies to | Meaning | Default |
|---|---|---|---|
| `PS_CORE_T_COAUTH` | Co-authorship | Min weighted degree (fractional papers) | `1.0` |
| `PS_CORE_T_BIB` | Bibliographic Coupling | Min weighted degree (cosine similarity sum) | `0.5` |
| `PS_CORE_T_CONCEPT` | Concept Co-occurrence | Min weighted degree (cosine similarity sum) | `1.0` |
| `PS_CORE_T_FIELD` | Research Field Sharing | Min weighted degree (cosine similarity sum) | `1.0` |

Output filenames encode the threshold, e.g. `coauthorship_norm_ps1.0.pkl`.

### Mode 2: Degree Threshold (`EXTRACTION_MODE = "threshold"`) — Legacy

Removes edges below a fixed weight and nodes below a fixed degree count.

| Parameter | Applies to | Meaning |
|---|---|---|
| `MIN_COAUTH_WEIGHT` | Co-authorship | Minimum normalized edge weight |
| `MIN_SHARED_REFS` | Bibliographic Coupling | Minimum normalized edge weight |
| `MIN_CONCEPT_COOC` | Concept Co-occurrence | Minimum normalized edge weight |
| `MIN_FIELD_COOC` | Research Field Sharing | Minimum normalized edge weight |
| `MIN_DEGREE` | All graphs | Minimum node degree after edge pruning |

Set any parameter to `0` for no filtering. Output filenames encode the parameters, e.g. `coauthorship_w0_d0.pkl`.

---

## Step 3 — Finding Visualization Thresholds

Two helper scripts identify the threshold values that yield a manageable number of nodes (~70–130) for interactive visualization.

### `find_thresholds.py` — Weighted Degree Thresholds

For each graph, computes the weighted degree of all nodes and reports the threshold values that yield approximately 130 and 70 nodes respectively.

**OpenAlex results (targeting ~130 nodes):**

| Graph | Threshold | Nodes |
|---|---|---|
| `bibliographic_coupling_norm_r0_d0.pkl` | weighted degree ≥ 154.8608 | 130 |
| `bibliographic_coupling_r0_d0.pkl` | weighted degree ≥ 7418.0 | 130 |
| `coauthorship_norm_w0_d0.pkl` | weighted degree ≥ 19.4639 | 129 |
| `coauthorship_w0_d0.pkl` | weighted degree ≥ 206.0 | 132 |
| `concept_cooccurrence_norm_c0_d0.pkl` | weighted degree ≥ 4.0 | 134 |
| `concept_cooccurrence_c0_d0.pkl` | weighted degree ≥ 222.0 | 130 |
| `field_sharing_f0_d0.pkl` | — | 26 (plot as-is) |
| `field_sharing_norm_f0_d0.pkl` | — | 26 (plot as-is) |

**Dimensions results (targeting ~130 nodes):**

| Graph | Threshold | Nodes |
|---|---|---|
| `bibliographic_coupling_norm_r0_d0.pkl` | weighted degree ≥ 139.7165 | 130 |
| `bibliographic_coupling_r0_d0.pkl` | weighted degree ≥ 7489.0 | 130 |
| `coauthorship_norm_w0_d0.pkl` | weighted degree ≥ 22.0 | 131 |
| `coauthorship_w0_d0.pkl` | weighted degree ≥ 3011.0 | 153 |
| `concept_cooccurrence_norm_c0_d0.pkl` | weighted degree ≥ 730.2469 | 130 |
| `concept_cooccurrence_c0_d0.pkl` | weighted degree ≥ 167731.0 | 130 |
| `field_sharing_f0_d0.pkl` | — | 70 (plot as-is) |
| `field_sharing_norm_f0_d0.pkl` | — | 70 (plot as-is) |

### `find_pscore_thresholds.py` — Ps-core Thresholds

Uses the Batagelj-Zaveršnik O(m) peeling algorithm to compute the full Ps-core decomposition in a single pass, then reports the threshold values yielding approximately 130 and 70 nodes.

**OpenAlex results (targeting ~130 nodes):**

| Graph | Ps-core threshold | Nodes |
|---|---|---|
| `bibliographic_coupling_norm_r0_d0.pkl` | t ≥ 48.9552 | 130 |
| `bibliographic_coupling_r0_d0.pkl` | t ≥ 3334.0 | 130 |
| `coauthorship_norm_w0_d0.pkl` | t ≥ 3.8333 | 130 |
| `coauthorship_w0_d0.pkl` | t ≥ 91.0 | 139 |
| `concept_cooccurrence_norm_c0_d0.pkl` | t ≥ 1.6592 | 130 |
| `concept_cooccurrence_c0_d0.pkl` | t ≥ 129.0 | 131 |
| `field_sharing_f0_d0.pkl` | — | 26 (plot as-is) |
| `field_sharing_norm_f0_d0.pkl` | — | 26 (plot as-is) |

**Dimensions results (targeting ~130 nodes):**

| Graph | Ps-core threshold | Nodes |
|---|---|---|
| `bibliographic_coupling_norm_r0_d0.pkl` | t ≥ 39.4638 | 130 |
| `bibliographic_coupling_r0_d0.pkl` | t ≥ 1181.0 | 130 |
| `coauthorship_norm_w0_d0.pkl` | t ≥ 4.3333 | 131 |
| `coauthorship_w0_d0.pkl` | t ≥ 2638.0 | 130 |
| `concept_cooccurrence_norm_c0_d0.pkl` | t ≥ 29.0 | 132 |
| `concept_cooccurrence_c0_d0.pkl` | t ≥ 38402.0 | 130 |
| `field_sharing_f0_d0.pkl` | — | 70 (plot as-is) |
| `field_sharing_norm_f0_d0.pkl` | — | 70 (plot as-is) |

---

## Step 4 — Visualization

### `run_visualizations.py` — Degree-threshold Visualizations

Generates interactive PyVis HTML files for all graphs using the weighted degree thresholds above. Run from each folder:

```bash
python run_visualizations.py
```

### `run_pscore_visualizations.py` — Ps-core Visualizations

Generates interactive PyVis HTML files using Ps-core extraction at the thresholds above. Run from each folder:

```bash
python run_pscore_visualizations.py
```

### `visualize_biblio_graphs.py` — Direct Visualization with Custom Parameters

For custom threshold values or single-graph visualization:

```bash
# Visualize a single graph with a specific weighted degree threshold
python visualize_biblio_graphs.py coauthorship_norm_w0_d0.pkl --min_degree 19.46

# Visualize without node labels (label shown only on hover) — useful for large graphs
python visualize_biblio_graphs.py concept_cooccurrence_c0_d0.pkl --no_labels

# Visualize all graphs in nx_graphs/ with no filtering
python visualize_biblio_graphs.py
```

All HTML files are self-contained (JavaScript embedded inline) and open directly in any browser without a server. Each file includes a title displaying the graph type, normalization method, and threshold used.

### PyVis Performance Guidelines

| Graph size | Rendering time | Recommendation |
|---|---|---|
| < 500 nodes, < 2,000 edges | Fast (< 10 s) | Ideal for interactive exploration |
| < 2,000 nodes, < 10,000 edges | Moderate (10–60 s) | Acceptable; disable physics after layout settles |
| < 5,000 nodes, < 50,000 edges | Slow (1–5 min) | Use with caution |
| > 5,000 nodes or > 50,000 edges | May freeze or crash | Increase thresholds or use VOSviewer |

### VOSviewer Export (`export_to_vosviewer.py`)

For large untruncated graphs, export to VOSviewer format:

```bash
python export_to_vosviewer.py
```

This writes map and network `.txt` files to `vosviewer_files/`, which can be opened directly in [VOSviewer](https://www.vosviewer.com/). VOSviewer handles graphs of hundreds of thousands of nodes efficiently and exports PNG/SVG screenshots suitable for publication.

---

## Notes

- The Dimensions DSL API imposes a pagination ceiling (typically 50,000 records via `skip`). If the corpus exceeds this limit, the script stops gracefully and reports the total fetched.
- All output directories (`data/`, `nx_graphs/`, `pyvis_graphs/`, `vosviewer_files/`) are created automatically on first run.
- Multiple versions of the same graph type produced with different thresholds coexist safely in `nx_graphs/` thanks to the stamped filename convention.
- The `find_pscore_thresholds.py` script uses the Batagelj-Zaveršnik O(m) peeling algorithm and completes in seconds even for graphs with hundreds of thousands of nodes and tens of millions of edges.

---

## Network Comparison Methodology

The core challenge in comparing OpenAlex and Dimensions is that the two databases represent the same underlying scholarly reality but produce non-identical node sets due to differences in coverage, author disambiguation (ORCID vs. Dimensions researcher IDs), concept taxonomies (OpenAlex concepts vs. Dimensions Fields of Research), and identifier standards. The comparison therefore operates at four complementary levels of analysis.

### 1. Structural Comparison (Full Graphs, No Alignment Required)

For each of the four network types, the full untruncated graphs from both databases are compared on the following global statistics:

- **Degree distribution**: log-log plots of the complementary cumulative degree distribution P(K ≥ k) for both raw and normalized graphs. A two-sample Kolmogorov-Smirnov test is used to assess whether the two distributions are statistically distinguishable.
- **Clustering coefficient**: global and average local clustering coefficients.
- **Assortativity**: degree assortativity coefficient (Newman, 2002), measuring whether high-degree nodes preferentially connect to other high-degree nodes.
- **Ps-core decomposition profile**: the distribution of Ps-core levels across nodes, computed via the Batagelj-Zaveršnik O(m) peeling algorithm (Batagelj & Zaveršnik, 2003). This provides a scale-invariant fingerprint of the network's hierarchical core-periphery structure.

These measures are database-agnostic and require no node alignment.

### 2. Node-Aligned Comparison (Intersection of Identifiable Nodes)

Where nodes can be matched across databases using persistent identifiers — ORCID for authors, DOI for papers, ROR for institutions — the comparison is extended to the aligned subgraph. On this intersection:

- **Centrality rank correlation**: weighted degree centrality, betweenness centrality, and PageRank are computed for each aligned node in both databases. Spearman's ρ and Kendall's τ are reported for each centrality measure, quantifying whether the two databases agree on which entities are most central.
- **Community structure overlap**: community detection (e.g., Louvain or label propagation) is run independently on each database's graph. The resulting partitions are compared on the aligned nodes using Normalised Mutual Information (NMI) and the Adjusted Rand Index (ARI), following Fortunato (2010).

### 3. Edge Overlap Analysis

For each network type, the edge sets of the two databases are compared on the aligned node intersection:

- **Jaccard similarity** of the edge sets: |E_OA ∩ E_DIM| / |E_OA ∪ E_DIM|.
- **Directed overlap**: the fraction of OA edges also present in Dimensions, and the fraction of Dimensions edges also present in OA. Asymmetry in these fractions reveals systematic coverage differences.
- **Weight correlation**: for edges present in both databases, the Spearman correlation of edge weights quantifies whether the two databases agree not just on the existence of a link but on its strength.

This approach directly quantifies coverage differences independently of node disambiguation, following the methodology of Visser, van Eck, & Waltman (2021).

### 4. Bayesian Parameter Comparison via QUAP

Points 1–3 provide descriptive and rank-based comparisons. Point 4 adds an uncertainty-aware, model-based comparison using Quadratic Approximation of the Posterior (QUAP), as introduced by McElreath (2020).

The degree distributions of bibliometric networks are well-described by a power law P(k) ∝ k^{−α} with a lower cutoff k_min (Barabási & Albert, 1999; Clauset, Shalizi, & Newman, 2009). For each network type and each database, a power-law model is fitted to the degree sequence. QUAP approximates the posterior distribution over the exponent α by fitting a Gaussian at the mode of the log-posterior, using the maximum likelihood estimator of Clauset et al. (2009) as the starting point.

The comparison then proceeds as follows:

- The posterior distributions p(α | OA) and p(α | DIM) are plotted for each network type.
- The **Bhattacharyya coefficient** BC = ∫ √(p₁(α) · p₂(α)) dα is computed as a measure of posterior overlap (BC = 1 indicates identical posteriors; BC = 0 indicates no overlap).
- The **Kullback-Leibler divergence** D_KL(p₁ ‖ p₂) is reported as a directed measure of how much information is lost when approximating one database's degree distribution with the other's model.
- **89% credible intervals** (following McElreath's convention) are compared: if the intervals overlap, the two databases are consistent with the same generative process at that credibility level.

This Bayesian framing moves the comparison from point estimates to full uncertainty quantification, and is more informative than a KS test p-value, which conflates effect size with sample size. The Gaussian approximation underlying QUAP is reasonable for α given large samples but may be inadequate for heavy-tailed distributions; in such cases, full MCMC sampling via PyMC or Stan is recommended as a robustness check.

### References

- Barabási, A.-L., & Albert, R. (1999). Emergence of scaling in random networks. *Science*, 286(5439), 509–512.
- Batagelj, V., & Zaveršnik, M. (2003). An O(m) algorithm for cores decomposition of networks. *arXiv:cs/0310049*.
- Clauset, A., Shalizi, C. R., & Newman, M. E. J. (2009). Power-law distributions in empirical data. *SIAM Review*, 51(4), 661–703.
- Fortunato, S. (2010). Community detection in graphs. *Physics Reports*, 486(3–5), 75–174.
- Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., & Rubin, D. B. (2013). *Bayesian Data Analysis* (3rd ed.). CRC Press.
- McElreath, R. (2020). *Statistical Rethinking: A Bayesian Course with Examples in R and Stan* (2nd ed.). CRC Press.
- Newman, M. E. J. (2002). Assortative mixing in networks. *Physical Review Letters*, 89(20), 208701.
- Visser, M., van Eck, N. J., & Waltman, L. (2021). Large-scale comparison of bibliographic data sources: Scopus, Web of Science, Dimensions, Crossref, and Microsoft Academic Scholar. *Quantitative Science Studies*, 2(1), 20–41.

---

## License

Copyright (c) 2026 Moses Boudourides. This project is licensed under the [MIT License](https://github.com/mboudour/Comparative-Bibiometric-Study-of-OpenAlex-Dimenions.ai/blob/main/LICENSE).
