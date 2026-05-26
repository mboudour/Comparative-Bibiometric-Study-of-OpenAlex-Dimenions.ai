import os
import time
import json
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

# Load Journals
try:
    journals_df = pd.read_csv("journals.csv")
    # We will query by ISSNs
    ISSNS = journals_df['issn'].tolist() + journals_df['issn_e'].dropna().tolist()
    ISSNS = list(set(ISSNS)) # Remove duplicates
except FileNotFoundError:
    print("journals.csv not found. Please ensure it is in the same directory.")
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
    
    issn_list_str = json.dumps(ISSNS)
    
    print(f"Fetching Dimensions data for {len(journals_df)} journals ({YEAR_START}-{YEAR_END})")
    
    while True:
        # We need: ID, DOI, Title, Year, Journal, Authors, References, Concepts, Fields (FOR)
        query = f"""
        search publications
        where journal.issn in {issn_list_str}
        and year in [{YEAR_START}:{YEAR_END}]
        and type = "article"
        return publications[id+doi+title+year+journal+authors+reference_ids+concepts+category_for]
        limit {limit} skip {skip}
        """
        
        try:
            data = query_dimensions(token, query)
        except requests.exceptions.HTTPError as e:
            if "Limit skip" in str(e) or e.response.status_code == 400:
                print("Pagination limit reached or bad request. Stopping pagination.")
                break
            else:
                raise e
        
        pubs = data.get("publications", [])
        if not pubs:
            break
            
        all_works.extend(pubs)
        print(f"Fetched {len(all_works)} works...")
        
        skip += limit
        time.sleep(1) # Be polite
        
    print(f"Total works fetched: {len(all_works)}")
    
    # Save the raw works catalog (nodes)
    catalog = []
    for w in all_works:
        catalog.append({
            "id": w.get("id"),
            "doi": w.get("doi"),
            "title": w.get("title"),
            "year": w.get("year"),
            "journal": w.get("journal", {}).get("title")
        })
    pd.DataFrame(catalog).to_csv(os.path.join(DATA_DIR, "dimensions_nodes.csv"), index=False)
    print("Saved dimensions_nodes.csv")
    
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
        authors = work.get("authors", [])
        author_ids = [a.get("researcher_id") for a in authors if a.get("researcher_id")]
        for i in range(len(author_ids)):
            for j in range(i+1, len(author_ids)):
                coauth_edges.append({"source": author_ids[i], "target": author_ids[j], "paper_id": work_id})
                
        # 2. Bibliographic Coupling
        refs = work.get("reference_ids", [])
        for ref in refs:
            bib_edges.append({"paper_id": work_id, "reference_id": ref})
            
        # 3. Concept Co-occurrence
        concepts = work.get("concepts", [])
        for c in concepts:
            # Dimensions concepts are strings; we create pseudo-IDs by lowercasing
            concept_edges.append({"paper_id": work_id, "concept_id": c.lower(), "concept_name": c})
                
        # 4. Field Sharing (FOR categories)
        categories = work.get("category_for", [])
        for cat in categories:
            # e.g., {'id': '4609', 'name': '4609 Information Systems'}
            field_edges.append({"paper_id": work_id, "field_id": cat.get("id"), "field_name": cat.get("name")})
            
    pd.DataFrame(coauth_edges).to_csv(os.path.join(DATA_DIR, "dimensions_coauth_edges.csv"), index=False)
    pd.DataFrame(bib_edges).to_csv(os.path.join(DATA_DIR, "dimensions_bib_edges.csv"), index=False)
    pd.DataFrame(concept_edges).to_csv(os.path.join(DATA_DIR, "dimensions_concept_edges.csv"), index=False)
    pd.DataFrame(field_edges).to_csv(os.path.join(DATA_DIR, "dimensions_field_edges.csv"), index=False)
    print("Network edge lists saved to CSV in 'data' folder.")

if __name__ == "__main__":
    fetch_dimensions_data()
