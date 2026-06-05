import os
import pickle
import requests
import time
import pandas as pd
from urllib.parse import urlencode

# =============================================================================
# CONFIGURATION
# =============================================================================
YEAR_START = 2010
YEAR_END = 2024

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Load email and optional API key from key.txt
# Line 1: contact email (for polite pool)
# Line 2: OpenAlex API key (optional — leave blank to skip)
try:
    with open("key.txt", "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]
        EMAIL = lines[0] if len(lines) > 0 else "your_email@example.com"
        API_KEY = lines[1] if len(lines) > 1 and lines[1] != "YOUR_OPENALEX_API_KEY_HERE" else None
except FileNotFoundError:
    print("key.txt not found. Please ensure it is in the same directory.")
    exit(1)

if API_KEY:
    print("Using OpenAlex API key.")
else:
    print("No OpenAlex API key provided. Proceeding with polite pool (email only).")

# Load Journals from shared top-level journals.csv
JOURNALS_CSV = os.path.join("..", "journals.csv")
try:
    journals_df = pd.read_csv(JOURNALS_CSV)
    JOURNALS = dict(zip(journals_df['journal_name'], journals_df['openalex_id']))
except FileNotFoundError:
    print(f"{JOURNALS_CSV} not found. Please ensure journals.csv is in the top project folder.")
    exit(1)

JOURNAL_IDS = "|".join(JOURNALS.values())

# All fields to fetch from OpenAlex
SELECT_FIELDS = ",".join([
    "id",
    "doi",
    "title",
    "publication_year",
    "primary_location",
    "authorships",
    "referenced_works",
    "concepts",
    "topics"
])

# =============================================================================
# FETCH DATA
# =============================================================================
def fetch_openalex_data():
    base_url = "https://api.openalex.org/works"
    cursor = "*"
    all_works = []

    print(f"Fetching OpenAlex data for {len(JOURNALS)} journals ({YEAR_START}-{YEAR_END})")

    while cursor:
        params = {
            "filter": f"primary_location.source.id:{JOURNAL_IDS},publication_year:{YEAR_START}-{YEAR_END},type:article",
            "select": SELECT_FIELDS,
            "per-page": 200,
            "cursor": cursor,
            "mailto": EMAIL
        }
        if API_KEY:
            params["api_key"] = API_KEY

        query_string = urlencode(params, safe="*,")
        url = f"{base_url}?{query_string}"

        response = requests.get(url)

        if response.status_code == 429:
            print("Rate limit hit. Waiting 5 seconds...")
            time.sleep(5)
            continue

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            break

        all_works.extend(results)
        cursor = data.get("meta", {}).get("next_cursor")

        print(f"Fetched {len(all_works)} works...")
        time.sleep(0.1)

    print(f"Total works fetched: {len(all_works)}")

    # -------------------------------------------------------------------------
    # Save 1: Full raw records as a pickled DataFrame (all fetched fields)
    # -------------------------------------------------------------------------
    df_raw = pd.DataFrame(all_works)
    raw_pkl_path = os.path.join(DATA_DIR, "openalex_raw.pkl")
    with open(raw_pkl_path, "wb") as f:
        pickle.dump(df_raw, f)
    print(f"Saved full raw DataFrame → {raw_pkl_path}  (shape: {df_raw.shape})")

    # -------------------------------------------------------------------------
    # Save 2: Flat nodes catalog CSV (key scalar fields only)
    # -------------------------------------------------------------------------
    catalog = []
    for w in all_works:
        catalog.append({
            "id":    w.get("id"),
            "doi":   w.get("doi"),
            "title": w.get("title"),
            "year":  w.get("publication_year"),
            "journal": w.get("primary_location", {}).get("source", {}).get("display_name")
        })
    nodes_path = os.path.join(DATA_DIR, "openalex_nodes.csv")
    pd.DataFrame(catalog).to_csv(nodes_path, index=False)
    print(f"Saved nodes catalog → {nodes_path}")

    process_networks(all_works)

# =============================================================================
# PROCESS NETWORKS
# =============================================================================
def process_networks(works):
    coauth_edges = []
    bib_edges = []
    concept_edges = []
    field_edges = []

    print("Processing networks...")
    for work in works:
        work_id = work.get("id")

        # 1. Co-authorship Edges
        authorships = work.get("authorships", [])
        author_ids = [a.get("author", {}).get("id") for a in authorships if a.get("author")]
        for i in range(len(author_ids)):
            for j in range(i + 1, len(author_ids)):
                coauth_edges.append({"source": author_ids[i], "target": author_ids[j], "paper_id": work_id})

        # 2. Bibliographic Coupling
        refs = work.get("referenced_works", [])
        for ref in refs:
            bib_edges.append({"paper_id": work_id, "reference_id": ref})

        # 3. Concept Co-occurrence
        concepts = work.get("concepts", [])
        for c in concepts:
            if c.get("score", 0) > 0.6:
                concept_edges.append({"paper_id": work_id, "concept_id": c.get("id"), "concept_name": c.get("display_name")})

        # 4. Field Sharing (Topics)
        topics = work.get("topics", [])
        for t in topics:
            field_edges.append({"paper_id": work_id, "field_id": t.get("field", {}).get("id"), "field_name": t.get("field", {}).get("display_name")})

    pd.DataFrame(coauth_edges).to_csv(os.path.join(DATA_DIR, "openalex_coauth_edges.csv"), index=False)
    pd.DataFrame(bib_edges).to_csv(os.path.join(DATA_DIR, "openalex_bib_edges.csv"), index=False)
    pd.DataFrame(concept_edges).to_csv(os.path.join(DATA_DIR, "openalex_concept_edges.csv"), index=False)
    pd.DataFrame(field_edges).to_csv(os.path.join(DATA_DIR, "openalex_field_edges.csv"), index=False)
    print("Network edge lists saved to CSV in 'data/' folder.")

if __name__ == "__main__":
    fetch_openalex_data()
