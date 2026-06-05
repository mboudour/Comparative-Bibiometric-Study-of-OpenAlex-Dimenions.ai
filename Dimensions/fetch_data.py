import os
import time
import json
import pickle
import requests
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================
YEAR_START = 2010
YEAR_END = 2024

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Load API Key
try:
    with open("key.txt", "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith("#")]
        if not lines or lines[0] == "YOUR_DIMENSIONS_API_KEY_HERE":
            print("Please insert your Dimensions API key in key.txt")
            exit(1)
        API_KEY = lines[0]
except FileNotFoundError:
    print("key.txt not found. Please ensure it is in the same directory.")
    exit(1)

# Load Journals from shared top-level journals.csv
JOURNALS_CSV = os.path.join("..", "journals.csv")
try:
    journals_df = pd.read_csv(JOURNALS_CSV)
    # Collect all unique ISSNs (print + electronic) for the ISSN filter
    issns_print = journals_df['issn'].dropna().tolist()
    issns_elec  = journals_df['issn_e'].dropna().tolist()
    ISSNS = list(set(issns_print + issns_elec))
except FileNotFoundError:
    print(f"{JOURNALS_CSV} not found. Please ensure journals.csv is in the top project folder.")
    exit(1)

# =============================================================================
# DIMENSIONS API HELPERS
# =============================================================================
def get_dimensions_token(api_key):
    url = "https://app.dimensions.ai/api/auth.json"
    payload = {"key": api_key}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json().get("token")

def query_dimensions(token, query):
    url = "https://app.dimensions.ai/api/dsl/v2"
    headers = {"Authorization": f"JWT {token}"}
    response = requests.post(url, headers=headers, data=query.encode('utf-8'))

    if response.status_code == 429:
        print("Rate limit hit. Waiting 30 seconds...")
        time.sleep(30)
        return query_dimensions(token, query)

    if not response.ok:
        print(f"DSL error {response.status_code}: {response.text[:300]}")
        response.raise_for_status()

    return response.json()

# =============================================================================
# FETCH DATA
# =============================================================================
def fetch_dimensions_data():
    print("Authenticating with Dimensions API...")
    token = get_dimensions_token(API_KEY)

    all_works = []
    limit = 1000
    skip = 0

    # Build ISSN list as a JSON array string for the DSL where clause
    issn_list_str = json.dumps(ISSNS)

    print(f"Fetching Dimensions data for {len(journals_df)} journals ({YEAR_START}-{YEAR_END})")
    print(f"Filtering on {len(ISSNS)} ISSNs...")

    while True:
        # Correct DSL syntax:
        # - Filter by publication-level `issn` field (not journal.issn)
        # - document_type = "Research Article" (Dimensions capitalised values)
        # - year range uses >= and <=
        query = f"""
        search publications
        where issn in {issn_list_str}
        and year >= {YEAR_START}
        and year <= {YEAR_END}
        and document_type = "Research Article"
        return publications[
            id + doi + title + year + journal + authors + researchers +
            reference_ids + concepts + concepts_scores + category_for +
            open_access + times_cited + field_citation_ratio
        ]
        limit {limit} skip {skip}
        """

        try:
            data = query_dimensions(token, query)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:
                err_text = e.response.text
                if "skip" in err_text.lower() or "limit" in err_text.lower():
                    print("Pagination ceiling reached. Stopping.")
                else:
                    print(f"Bad request: {err_text[:300]}")
                break
            raise

        pubs = data.get("publications", [])
        if not pubs:
            print("No more results returned.")
            break

        all_works.extend(pubs)
        print(f"Fetched {len(all_works)} works so far...")

        skip += limit
        time.sleep(1)  # Be polite

    print(f"Total works fetched: {len(all_works)}")

    # -------------------------------------------------------------------------
    # Save 1: Full raw records as a pickled DataFrame (all fetched fields)
    # -------------------------------------------------------------------------
    df_raw = pd.DataFrame(all_works)
    raw_pkl_path = os.path.join(DATA_DIR, "dimensions_raw.pkl")
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
            "year":  w.get("year"),
            "journal": w.get("journal", {}).get("title") if isinstance(w.get("journal"), dict) else w.get("journal")
        })
    nodes_path = os.path.join(DATA_DIR, "dimensions_nodes.csv")
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
        # Use `researchers` for disambiguated researcher IDs; fall back to `authors` names
        researchers = work.get("researchers", [])
        if researchers:
            author_ids = [r.get("id") for r in researchers if r.get("id")]
        else:
            authors = work.get("authors", [])
            author_ids = [
                a.get("researcher_id") or a.get("id") or a.get("name")
                for a in authors
                if a.get("researcher_id") or a.get("id") or a.get("name")
            ]
        for i in range(len(author_ids)):
            for j in range(i + 1, len(author_ids)):
                coauth_edges.append({"source": author_ids[i], "target": author_ids[j], "paper_id": work_id})

        # 2. Bibliographic Coupling
        refs = work.get("reference_ids", [])
        for ref in refs:
            bib_edges.append({"paper_id": work_id, "reference_id": ref})

        # 3. Concept Co-occurrence
        # concepts_scores gives [{concept, score}]; concepts gives a list of strings
        concepts_scores = work.get("concepts_scores", [])
        if concepts_scores:
            for cs in concepts_scores:
                concept_name = cs.get("concept", "")
                score = cs.get("score", 0)
                if score >= 0.6 and concept_name:
                    concept_edges.append({"paper_id": work_id, "concept_id": concept_name.lower(), "concept_name": concept_name})
        else:
            for c in work.get("concepts", []):
                if isinstance(c, str) and c:
                    concept_edges.append({"paper_id": work_id, "concept_id": c.lower(), "concept_name": c})

        # 4. Field Sharing (FOR categories)
        categories = work.get("category_for", [])
        for cat in categories:
            if isinstance(cat, dict):
                field_edges.append({"paper_id": work_id, "field_id": cat.get("id"), "field_name": cat.get("name")})

    pd.DataFrame(coauth_edges).to_csv(os.path.join(DATA_DIR, "dimensions_coauth_edges.csv"), index=False)
    pd.DataFrame(bib_edges).to_csv(os.path.join(DATA_DIR, "dimensions_bib_edges.csv"), index=False)
    pd.DataFrame(concept_edges).to_csv(os.path.join(DATA_DIR, "dimensions_concept_edges.csv"), index=False)
    pd.DataFrame(field_edges).to_csv(os.path.join(DATA_DIR, "dimensions_field_edges.csv"), index=False)
    print("Network edge lists saved to CSV in 'data/' folder.")

if __name__ == "__main__":
    fetch_dimensions_data()
