# Comparative Bibliometric Study: OpenAlex & Dimensions.ai

A reproducible data collection and network analysis pipeline for comparing scientometric networks derived from the **OpenAlex** (open) and **Dimensions.ai** (proprietary) bibliographic databases.

This project supports the study:

> *"Do Open and Proprietary Bibliographic Databases Produce Equivalent Scientometric Networks? A Comparative Study of OpenAlex and Dimensions.ai"*

---

## Project Structure

```
ComparativeBibioStudyOpenAlex&Dimenions/
├── README.md
├── OpenAlex/
│   ├── key.txt                    ← Contact email (line 1) and optional API key (line 2)
│   ├── journals.csv               ← 18 target journals with OpenAlex Source IDs
│   ├── fetch_data.py              ← Step 1: Fetch publications and extract edge lists
│   ├── create_biblio_graphs.py    ← Step 2: Build, normalize, and pickle NetworkX graphs
│   ├── visualize_biblio_graphs.py ← Step 3: Generate interactive PyVis HTML visualizations
│   ├── data/                      ← Output: raw CSV edge lists (auto-created)
│   ├── nx_graphs/                 ← Output: pickled NetworkX graph objects (auto-created)
│   └── pyvis_graphs/              ← Output: interactive HTML visualizations (auto-created)
│
└── Dimensions/
    ├── key.txt                    ← Dimensions.ai API key
    ├── journals.csv               ← 18 target journals with print and electronic ISSNs
    ├── fetch_data.py              ← Step 1: Fetch publications via DSL API and extract edge lists
    ├── create_biblio_graphs.py    ← Step 2: Build, normalize, and pickle NetworkX graphs
    ├── visualize_biblio_graphs.py ← Step 3: Generate interactive PyVis HTML visualizations
    ├── data/                      ← Output: raw CSV edge lists (auto-created)
    ├── nx_graphs/                 ← Output: pickled NetworkX graph objects (auto-created)
    └── pyvis_graphs/              ← Output: interactive HTML visualizations (auto-created)
```

---

## Journal Corpus

18 journals across three thematic clusters, covering the period **2010–2024** (~40,000–45,000 articles).

| Journal | ISSN | Cluster |
|---|---|---|
| Scientometrics | 0138-9130 | Scientometrics & Informetrics |
| Journal of Informetrics | 1751-1577 | Scientometrics & Informetrics |
| Quantitative Science Studies | 2641-3337 | Scientometrics & Informetrics |
| Research Evaluation | 0958-2029 | Scientometrics & Informetrics |
| JASIST | 2330-1635 | Scientometrics & Informetrics |
| Information Processing & Management | 0306-4573 | Information Science |
| Journal of Information Science | 0165-5515 | Information Science |
| Aslib Journal of Information Management | 2050-3806 | Information Science |
| Library & Information Science Research | 0740-8188 | Information Science |
| Online Information Review | 1468-4527 | Information Science |
| Journal of Documentation | 0022-0418 | Information Science |
| The Lancet Digital Health | 2589-7500 | AI in Health / Medicine |
| npj Digital Medicine | 2398-6352 | AI in Health / Medicine |
| Artificial Intelligence in Medicine | 0933-3657 | AI in Health / Medicine |
| JAMIA | 1527-974X | AI in Health / Medicine |
| Journal of Medical Internet Research | 1438-8871 | AI in Health / Medicine |
| Journal of Biomedical Informatics | 1532-0464 | AI in Health / Medicine |
| Digital Health | 2055-2076 | AI in Health / Medicine |

---

## Four Scientometric Networks and Normalization

Each pipeline produces four network types. Because raw counts can be heavily biased by paper size (e.g., medical papers often have many more authors and references than scientometrics papers) or hub entities (e.g., highly frequent concepts), **fractional or cosine normalization is applied during graph creation**.

| Network | Description | Node Type | Edge Criterion | Normalization Applied |
|---|---|---|---|---|
| **Co-authorship** | Authors linked by shared publications | Author | Co-authored at least one paper | **Strict Fractional** (weight += 1/max(1, k-1) per paper, where k = authors) |
| **Bibliographic Coupling** | Papers linked by shared references | Paper | Cite at least one common reference | **Cosine** (normalized by reference list lengths) |
| **Concept Co-occurrence** | Concepts linked by co-assignment to the same paper | Concept / Keyword | Appear together in at least one paper | **Cosine** (normalized by concept frequencies) |
| **Research Field Sharing** | Research fields linked by co-assignment to the same paper | Field / FOR Category | Co-assigned to at least one paper | **Cosine** (normalized by field frequencies) |

---

## Prerequisites

Install the required Python packages before running any scripts:

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
- **Line 2:** your OpenAlex API key (optional — leave blank or remove the line if you do not have one)

To request an OpenAlex API key visit: [https://openalex.org/](https://openalex.org/)

### Dimensions.ai

A Dimensions API key is required. To obtain one:
- Visit [https://www.dimensions.ai/contact-us/](https://www.dimensions.ai/contact-us/) or request access via the [Digital Science API portal](https://www.digital-science.com/resource/dimensions-apis/).

Edit `Dimensions/key.txt`:
```
YOUR_DIMENSIONS_API_KEY_HERE
```

---

## Running the Pipeline

Run the three scripts in sequence from within each subfolder. **Always `cd` into the subfolder first**, as all paths are relative.

### OpenAlex

```bash
cd OpenAlex
python fetch_data.py
python create_biblio_graphs.py
python visualize_biblio_graphs.py
```

### Dimensions

```bash
cd Dimensions
python fetch_data.py
python create_biblio_graphs.py
python visualize_biblio_graphs.py
```

---

## Script Details

### `fetch_data.py`

Fetches all articles from the 18 target journals within the 2010–2024 window and extracts raw edge lists for each of the four network types.

**OpenAlex:** Uses cursor-based pagination (200 records per page) against the `/works` endpoint, filtering by `primary_location.source.id`, `publication_year`, and `type:article`. Fields fetched: `id`, `doi`, `title`, `publication_year`, `primary_location`, `authorships`, `referenced_works`, `concepts`, `topics`.

**Dimensions:** Authenticates via `POST /api/auth.json` to obtain a JWT token, then issues DSL queries using `limit`/`skip` pagination, filtering by ISSN list, year range, and `type = "article"`. Fields fetched: `id`, `doi`, `title`, `year`, `journal`, `authors`, `reference_ids`, `concepts`, `category_for`.

**Outputs to `data/`:**

| File | Contents |
|---|---|
| `*_nodes.csv` | Full article catalog (id, doi, title, year, journal) |
| `*_coauth_edges.csv` | Author–author pairs per paper |
| `*_bib_edges.csv` | Paper–reference pairs |
| `*_concept_edges.csv` | Paper–concept pairs |
| `*_field_edges.csv` | Paper–field pairs |

---

### `create_biblio_graphs.py`

Reads the CSV edge lists and constructs four normalized NetworkX graphs, serialised as pickle files.

The script offers two **Extraction Modes** to manage graph size and extract the core structure:
1. **Ps-core Extraction (Recommended):** Extracts the maximal subgraph where every node's weighted degree is at least *t*. This is a principled, scale-invariant, data-driven approach that identifies the productive backbone of the network.
2. **Threshold Curtailing (Legacy):** Removes edges below a fixed weight and nodes below a fixed degree.

Set `EXTRACTION_MODE` at the top of the script to either `"ps_core"` or `"threshold"`.

#### Ps-core Parameters (`EXTRACTION_MODE = "ps_core"`)

| Parameter | Meaning | Recommended Start | Output suffix |
|---|---|---|---|
| `PS_CORE_T_COAUTH` | Min weighted degree (fractional papers) | `1.0` | `norm_ps1.0.pkl` |
| `PS_CORE_T_BIB` | Min weighted degree (cosine similarity sum) | `0.5` | `norm_ps0.5.pkl` |
| `PS_CORE_T_CONCEPT` | Min weighted degree (cosine similarity sum) | `1.0` | `norm_ps1.0.pkl` |
| `PS_CORE_T_FIELD` | Min weighted degree (cosine similarity sum) | `1.0` | `norm_ps1.0.pkl` |

#### Threshold Parameters (`EXTRACTION_MODE = "threshold"`)

| Parameter | Applies to | Meaning |
|---|---|---|
| `MIN_COAUTH_WEIGHT` | Co-authorship | Minimum normalized weight for an edge to be kept |
| `MIN_SHARED_REFS` | Bibliographic Coupling | Minimum normalized weight for an edge to be kept |
| `MIN_CONCEPT_COOC` | Concept Co-occurrence | Minimum normalized weight for an edge to be kept |
| `MIN_FIELD_COOC` | Research Field Sharing | Minimum normalized weight for an edge to be kept |
| `MIN_DEGREE` | All graphs | Minimum node degree applied after edge pruning; removes peripheral nodes |

Set any parameter to `0` to apply no filtering for that criterion. The threshold values are encoded directly into the output filename (e.g., `norm_w3_d2.pkl`), so multiple versions can coexist in `nx_graphs/` without overwriting each other.

---

### `visualize_biblio_graphs.py`

Loads pickled NetworkX graphs and renders them as self-contained interactive HTML files using **PyVis**, with a white background and all interactive controls enabled (physics simulation, node styling, edge styling).

#### Targeting Specific Graphs

Run without arguments to visualise **all** `.pkl` files currently in `nx_graphs/`:

```bash
python visualize_biblio_graphs.py
```

Pass one or more filenames to visualise **specific graphs** only:

```bash
python visualize_biblio_graphs.py coauthorship_norm_ps1.0.pkl
python visualize_biblio_graphs.py coauthorship_norm_ps1.0.pkl concept_cooccurrence_norm_ps1.0.pkl
```

The output HTML is saved to `pyvis_graphs/` with the same base name as the `.pkl` file (e.g. `coauthorship_norm_ps1.0_vis.html`). Open any `.html` file directly in a web browser — no server required.

#### PyVis Performance Guidelines

The table below gives indicative rendering times on a modern machine with ~8 GB RAM. These are approximate and depend on browser, hardware, and physics simulation settings.

| Graph size | Rendering time | Recommendation |
|---|---|---|
| < 500 nodes, < 2,000 edges | Fast (< 10 seconds) | Ideal for interactive exploration |
| < 2,000 nodes, < 10,000 edges | Moderate (10–60 seconds) | Acceptable; disable physics after layout settles |
| < 5,000 nodes, < 50,000 edges | Slow (1–5 minutes) | Use with caution; increase thresholds if possible |
| > 5,000 nodes or > 50,000 edges | May freeze or crash the browser | Re-run `create_biblio_graphs.py` with higher Ps-core thresholds |

The script prints a warning if the loaded graph exceeds the safe threshold (5,000 nodes or 50,000 edges).

---

## Notes

- The Dimensions DSL API imposes a pagination ceiling (typically 50,000 records via `skip`). If the corpus exceeds this limit, the script will stop gracefully and report the total fetched.
- All output directories (`data/`, `nx_graphs/`, `pyvis_graphs/`) are created automatically on first run.
- Multiple versions of the same graph type (produced with different thresholds) coexist safely in `nx_graphs/` thanks to the stamped filename convention.
