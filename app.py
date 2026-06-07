"""
Streamlit App — How Much Do Scientometric Conclusions Depend on the Data Source?
Displays interactive PyVis network visualizations for OpenAlex and Dimensions.ai
"""

import streamlit as st
import os

st.set_page_config(
    page_title="How Much Do Scientometric Conclusions Depend on the Data Source?",
    layout="wide",
)

st.title("How Much Do Scientometric Conclusions Depend on the Data Source?")
st.markdown(
    "**A Cross-Disciplinary Analysis of OpenAlex and Dimensions Networks "
    "in Scientometrics, Information Science, and Digital Health (2010–2024)**"
)
st.markdown("---")

# ---------------------------------------------------------------------------
# File catalogue
# Each entry: (display_label, filename, database, graph_type, method)
# ---------------------------------------------------------------------------

OA_FILES = {
    "Co-authorship — Degree threshold (≥19.46, ~130 nodes)": "coauthorship_norm_w0_d0_d19.4639_vis.html",
    "Co-authorship — Ps-core threshold (4.82, ~70 nodes)":   "coauthorship_norm_w0_d0_ps4.8167_vis.html",
    "Bibliographic Coupling — Degree threshold (≥154.86, ~130 nodes)": "bibliographic_coupling_norm_r0_d0_d154.8608_vis.html",
    "Concept Co-occurrence — Degree threshold (≥4.0, ~134 nodes)":     "concept_cooccurrence_norm_c0_d0_d4.0_vis.html",
    "Concept Co-occurrence — Ps-core threshold (2.0, ~98 nodes)":       "concept_cooccurrence_norm_c0_d0_ps2.0_vis.html",
    "Research Field Sharing — Full graph":                              "field_sharing_norm_f0_d0_vis.html",
}

DIM_FILES = {
    "Co-authorship — Degree threshold (≥22.0, ~130 nodes)":  "coauthorship_norm_w0_d0_d22.0_vis.html",
    "Co-authorship — Ps-core threshold (5.53, ~105 nodes)":  "coauthorship_norm_w0_d0_ps5.5333_vis.html",
    "Bibliographic Coupling — Degree threshold (≥139.72, ~130 nodes)": "bibliographic_coupling_norm_r0_d0_d139.7165_vis.html",
    "Concept Co-occurrence — Ps-core threshold (31.0, ~71 nodes)":      "concept_cooccurrence_norm_c0_d0_ps31.0_vis.html",
    "Concept Co-occurrence — Ps-core threshold (2.0, ~98 nodes)":       "concept_cooccurrence_norm_c0_d0_ps2.0_vis.html",
    "Research Field Sharing — Full graph":                              "field_sharing_norm_f0_d0_vis.html",
}

DATABASE_MAP = {
    "OpenAlex": ("OpenAlex/pyvis_graphs", OA_FILES),
    "Dimensions": ("Dimensions/pyvis_graphs", DIM_FILES),
}

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.header("Network Selection")

database = st.sidebar.selectbox(
    "Database",
    options=list(DATABASE_MAP.keys()),
)

folder, file_map = DATABASE_MAP[database]
graph_label = st.sidebar.selectbox(
    "Graph",
    options=list(file_map.keys()),
)

filename = file_map[graph_label]
html_path = os.path.join(os.path.dirname(__file__), folder, filename)

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    st.components.v1.html(html_content, height=820, scrolling=False)
else:
    st.warning(f"Visualization file not found: `{filename}`")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Note:** All graphs show normalized networks only. "
    "Node size is constant (5). Labels appear on hover."
)
st.sidebar.markdown(
    "© 2026 Moses Boudourides — MIT License"
)
