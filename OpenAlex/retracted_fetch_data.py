import os
import time
import requests
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================
YEAR_START = 2010
YEAR_END   = 2024
BASE_URL   = "https://api.openalex.org/works"
DATA_DIR   = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Load credentials from key.txt
# Line 1: contact email (required for polite pool)
# Line 2: API key (optional — leave blank if not available)
try:
    with open("key.txt", "r") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    EMAIL   = lines[0] if len(lines) > 0 else ""
    API_KEY = lines[1] if len(lines) > 1 else ""
except FileNotFoundError:
    print("key.txt not found. Please ensure it is in the OpenAlex/ folder.")
    exit(1)

if EMAIL:
    print(f"Using contact email: {EMAIL}")
if API_KEY:
    print("Using OpenAlex API key.")

# Load journal source IDs from the shared top-level journals.csv
JOURNALS_CSV = os.path.join("..", "journals.csv")
try:
    journals_df = pd.read_csv(JOURNALS_CSV)
    SOURCE_IDS  = journals_df["openalex_id"].dropna().tolist()
    # Strip full URL prefix if present, keep only the S-prefixed ID
    SOURCE_IDS  = [s.replace("https://openalex.org/", "").strip() for s in SOURCE_IDS]
except FileNotFoundError:
    print(f"{JOURNALS_CSV} not found. Please ensure journals.csv is in the top project folder.")
    exit(1)

print(f"Fetching retraction flags for {len(SOURCE_IDS)} journals ({YEAR_START}-{YEAR_END})")

# =============================================================================
# FETCH
# =============================================================================
def build_params(cursor="*"):
    params = {
        "filter": (
            "primary_location.source.id:" + "|".join(SOURCE_IDS)
            + f",publication_year:{YEAR_START}-{YEAR_END}"
            + ",type:article"
        ),
        "select": "id,is_retracted,is_paratext",
        "per-page": 200,
        "cursor": cursor,
    }
    if EMAIL:
        params["mailto"] = EMAIL
    if API_KEY:
        params["api_key"] = API_KEY
    return params

records = []
cursor  = "*"
page    = 0

while True:
    params   = build_params(cursor)
    response = requests.get(BASE_URL, params=params)

    if response.status_code == 429:
        print("Rate limit hit. Waiting 10 seconds...")
        time.sleep(10)
        continue

    response.raise_for_status()
    data    = response.json()
    results = data.get("results", [])

    if not results:
        break

    for r in results:
        records.append({
            "OA_id":        r.get("id"),
            "is_retracted": r.get("is_retracted"),
            "is_paratext":  r.get("is_paratext"),
        })

    page  += 1
    cursor = data.get("meta", {}).get("next_cursor")
    print(f"Page {page:4d} — cumulative records: {len(records)}")

    if not cursor:
        break

    time.sleep(0.1)   # polite delay

# =============================================================================
# SAVE
# =============================================================================
out_path = os.path.join(DATA_DIR, "openalex_retraction_flags.csv")
df = pd.DataFrame(records, columns=["OA_id", "is_retracted", "is_paratext"])
df.to_csv(out_path, index=False)

print(f"\nTotal records fetched : {len(df)}")
print(f"Retracted             : {df['is_retracted'].sum()}")
print(f"Paratext              : {df['is_paratext'].sum()}")
print(f"Saved → {out_path}")
